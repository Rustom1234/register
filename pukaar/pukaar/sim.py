"""Simulation engine — makes the demo alive without real people.

Responders move through the pilot zone on a sim clock (config.sim_speed
sim-seconds per real second), receive offers from the real dispatch
engine, accept with GoodSAM-informed probabilities, travel, and close
cases with realistic outcome mixes. Witness scenarios drive the REAL
intake pipeline — nothing in the demo bypasses the production code path.
"""

from __future__ import annotations

import json
import math
import random
import threading
import time

from . import geo, routing
from .config import Config
from .db import new_id
from .service import PukaarService

RESPONDER_SEED = [
    ("Meena", True, "walk"), ("Arjun", False, "cycle"), ("Fatima", True, "walk"),
    ("Ravi", False, "scooter"), ("Sunita", False, "cycle"), ("Imran", False, "scooter"),
]

# Movement pace per travel mode, metres per sim-second. The router prices
# edges per road class; movement uses the mode's flat urban average so the
# dot's arrival matches the ETA we display (remaining metres / this speed).
MODE_SPEED_MPS = {"walk": 1.4, "cycle": 3.3, "scooter": 5.6}

# Kit depots — placeholder NGO locations until the partner supplies real
# ones (founder decision 2026-08-01: placeholders for now). Kits live HERE,
# not in riders' bags: dispatch routes the rider via the cheapest-detour
# depot that has the kit, and stock/restock is tracked per depot.
DEPOT_SEED = [
    ("depot_basti", "Basti Office", 28.5936, 77.2455),
    ("depot_east", "Nizamuddin East Community Room", 28.5878, 77.2585),
    ("depot_station", "Station-side Partner Shop", 28.5872, 77.2540),
]
# depot_id -> {sku: seed count}; totals match the old single-store world.
DEPOT_STOCK_SEED = {
    "depot_basti":   {"MED-1": 8, "FOOD-1": 10, "SEAS-M": 6},
    "depot_east":    {"MED-1": 6, "FOOD-1": 8, "SEAS-M": 5},
    "depot_station": {"MED-1": 4, "FOOD-1": 6, "SEAS-M": 4},
}

OUTCOME_WEIGHTS = [("served", 0.72), ("escalated", 0.08), ("declined", 0.08), ("not_found", 0.12)]

SCENARIOS = {
    "injured_flyover": [
        ("text", "Bhaiya flyover ke neeche ek aadmi hai, pair mein patti hai aur khoon dikh raha hai"),
        ("location", None),
        ("photo", "wrapped foot, blood visible through bandage, man sitting under flyover"),
        ("button", "fresh:10"),
    ],
    "family_rain": [
        ("text", "Mandir ke paas ek family baarish mein bheeg rahi hai, chhota baccha bhi hai"),
        ("location", None),
        ("button", "cat:shelter"),
        ("button", "fresh:10"),
    ],
    "hungry_elder": [
        ("text", "Station ke bahar ek buzurg do din se bhooke lag rahe hain"),
        ("location", None),
        ("button", "cat:food"),
        ("button", "fresh:60"),
    ],
    "emergency_112": [
        ("text", "Ek aadmi behosh pada hai sadak par!!"),
    ],
    "duplicate_burst": None,  # handled specially: three witnesses, same spot
    "golden_run": None,       # handled specially: guaranteed clean P1 arc
}


class Sim:
    def __init__(self, svc: PukaarService, cfg: Config, seed: int = 7):
        self.svc = svc
        self.cfg = cfg
        self.rng = random.Random(seed)
        # Real road graph when the demo-zone GeoJSON is present (the normal
        # case — it ships with the package); the old synthetic mesh only as
        # a last-resort fallback so the demo can never fail to boot.
        try:
            self.graph: routing.RoadGraph | None = routing.RoadGraph()
        except FileNotFoundError:
            self.graph = None
        self.mesh = routing.RoadMesh(cfg.zone_lat, cfg.zone_lng, cfg.zone_radius_m)
        # Depot pins snapped onto the street network so the box sits ON a
        # road, not in a courtyard — placeholder coords are hand-guessed.
        self.depot_list: list[tuple[str, str, float, float]] = []
        for depot_id, name, lat, lng in DEPOT_SEED:
            if self.graph is not None:
                snap = self.graph._snap(lat, lng, routing.SPEEDS_KMH["walk"])
                if snap is not None:
                    lat, lng = snap.lat, snap.lng
            self.depot_list.append((depot_id, name, lat, lng))
        self.sim_now = 8 * 3600.0          # 08:00 sim time, day 0
        # PUKAAR_DB persistence: resume the sim clock rather than rewinding
        # under persisted records (a rewound clock inverts every dedup /
        # recheck / retention time comparison), and re-arm the in-memory
        # escalation timers that died with the previous process.
        stored = svc.store.one("SELECT v FROM push_meta WHERE k='sim_now'")
        if stored:
            try:
                self.sim_now = max(self.sim_now, float(stored["v"]))
            except (TypeError, ValueError):
                pass
        self.running = True
        self.speed = cfg.sim_speed
        self.ambient = cfg.sim_ambient     # False = calm boot: see config.py
        # Kinetic state (_resp, manual, _reservations, positions) is touched
        # by the tick loop (event-loop thread) AND by sync endpoints on the
        # threadpool (duty flips, outcome settles). SQLite has its own lock
        # in db.py; this one serializes the in-memory compound updates.
        self._klock = threading.RLock()
        self.manual: set[str] = set()      # responders a human is playing via the UI
        self.golden: dict[str, str] = {}   # order_id -> chosen responder (scripted clean arc)
        self._restock_flagged: set[tuple[str, str]] = set()          # (depot, sku)
        self._pending_restocks: dict[tuple[str, str], float] = {}    # (depot, sku) -> due
        self._reservations: dict[str, tuple[str, str]] = {}          # order_id -> (depot, sku)
        # The kit ledger offsets DURABLE inventory rows (stock leaves at
        # accept), so the ledger must be durable too: a restart mid-delivery
        # must neither re-consume at re-attach (_on_accept's `already` guard
        # only works if reservations survive) nor orphan the eventual
        # settle_kit return, nor forget a courier restock already owed.
        stored = svc.store.one("SELECT v FROM push_meta WHERE k='kit_ledger'")
        if stored:
            try:
                led = json.loads(stored["v"])
                self._reservations = {k: (v[0], v[1])
                                      for k, v in led.get("reservations", {}).items()}
                self._pending_restocks = {tuple(k.split("|", 1)): float(v)
                                          for k, v in led.get("restocks", {}).items()}
                self._restock_flagged = set(self._pending_restocks)
            except (TypeError, ValueError, KeyError, IndexError):
                pass
        self._phone_counter = 0
        self._resp: dict[str, dict] = {}
        self._decides: dict[str, float] = {}   # assignment_id -> decision due (per-offer, not per-responder)
        self._coord_next = 0.0                 # the sim plays the coordinator too
        self._pending_escalations: dict[str, float] = {}
        # Ambient mode files its own witness reports; calm mode never does —
        # every case on a calm board is one a human actually created.
        self._random_report_at = (self.sim_now + self.rng.uniform(60, 240)
                                  if self.ambient else math.inf)
        self._pace_hold: float | None = None   # speed to restore after auto-pacing
        self.last_tick_real = time.monotonic()   # /health watchdog signal
        # Every close path must settle the kit ledger; the witness-recheck
        # cancel lives in service.py, which can't import sim — hook it here.
        svc.kit_settler = self.settle_kit
        self._seed_world()

    # -------------------------------------------------------------- setup --
    def _seed_world(self) -> None:
        # Stock lives at depots (inventory.partner_id carries the depot id).
        # IGNORE, not REPLACE: a PUKAAR_DB restart must not silently reset
        # depot stock that real activity has moved.
        for depot_id, stock in DEPOT_STOCK_SEED.items():
            for sku, count in stock.items():
                self.svc.store.execute(
                    "INSERT OR IGNORE INTO inventory (partner_id, sku, count, restock_threshold) "
                    "VALUES (?, ?, ?, 3)", (depot_id, sku, count))
        # Re-arm escalation timers for orders persisted mid-escalation — the
        # previous process's in-memory timers died with it.
        for row in self.svc.store.query("SELECT id FROM orders WHERE status='escalated'"):
            self._pending_escalations[row["id"]] = self.sim_now + self.rng.uniform(600, 1500)
        for i, (name, medical, mode) in enumerate(RESPONDER_SEED):
            rid = f"resp_{i+1}"
            self.svc.store.insert("responders", {
                "id": rid, "partner_id": "partner_1", "display_name": name,
                "medical": int(medical), "vetting": "verified",
                "active": 1 if self.ambient else 0,
            })
            # Ambient: scattered around the zone, already working. Calm: a
            # deterministic on-road home spot near "their" depot, off duty
            # and off the map until someone flips them on.
            lat, lng = (self._random_point(0.85) if self.ambient
                        else self._home_spot(i))
            self._resp[rid] = {
                "id": rid, "name": name, "medical": medical, "lat": lat, "lng": lng,
                "mode": mode, "speed": MODE_SPEED_MPS[mode],   # m per sim-second
                "accept_p": self.rng.uniform(0.55, 0.85),      # GoodSAM band, generous end
                "state": "idle", "order_id": None, "target": None, "on_duty": self.ambient,
                "dwell_until": None, "route": None, "route_idx": 0, "steps": None,
                "depot_id": None, "depot_name": None, "pickup_idx": None, "picked_up": True,
            }
            if self.ambient:
                self.svc.positions[rid] = (lat, lng)

    def _home_spot(self, i: int) -> tuple[float, float]:
        """Calm-mode start position for rider i: a spot a few hundred metres
        from their depot, snapped onto the street network so the first trip
        never begins with an off-road hop."""
        depot = self.depot_list[i % len(self.depot_list)]
        offs = [(0.0028, 0.0012), (-0.0022, 0.0026), (0.0009, -0.0031)]
        dlat, dlng = offs[(i // len(self.depot_list)) % len(offs)]
        lat, lng = depot[2] + dlat, depot[3] + dlng
        if self.graph is not None:
            snap = self.graph._snap(lat, lng, routing.SPEEDS_KMH["walk"])
            if snap is not None:
                return snap.lat, snap.lng
        return lat, lng

    def set_duty(self, rid: str, on: bool, manual: bool = False) -> bool:
        """Flip a rider on or off duty — the calm-mode entry point, driven
        by the rider app's duty button and the supervisor roster toggle.
        On duty: appear on the map at the current spot and join the
        dispatch candidate pool. Off duty: leave both — but never mid-job;
        a rider with an open order stays until it closes."""
        r = self._resp.get(rid)
        if not r:
            return False
        with self._klock:
            return self._set_duty_locked(r, rid, on, manual)

    def _set_duty_locked(self, r: dict, rid: str, on: bool, manual: bool) -> bool:
        if manual:
            (self.manual.add if on else self.manual.discard)(rid)
            if not on and self.ambient:
                # Ambient board: releasing the takeover hands the rider back
                # to the sim — it does NOT bench them. Only the calm board
                # treats the rider app's duty-off as leaving the shift.
                return True
        if on and not r.get("on_duty", True):
            r["on_duty"] = True
            self.svc.positions[rid] = (r["lat"], r["lng"])
            self.svc.set_active(rid, True)     # emits roster_change for the feed
        elif not on and r.get("on_duty", True):
            r["on_duty"] = False
            if r["state"] == "idle":
                self.svc.positions.pop(rid, None)
            self.svc.set_active(rid, False)
        return True

    def _route_to(self, r: dict, tlat: float, tlng: float) -> list[tuple[float, float]]:
        """Waypoints for r to reach (tlat, tlng) by its travel mode, over
        the real road graph when available."""
        return self._route_between(r["mode"], r["lat"], r["lng"], tlat, tlng)

    def _route_between(self, mode: str, alat: float, alng: float,
                       blat: float, blng: float) -> list[tuple[float, float]]:
        if self.graph is not None:
            return self.graph.route(alat, alng, blat, blng, mode=mode)[0]
        return self.mesh.route(alat, alng, blat, blng)[0]

    def _route_named(self, mode: str, alat: float, alng: float, blat: float,
                     blng: float) -> tuple[list[tuple[float, float]], list[str]]:
        """(waypoints, per-waypoint street names) — all "" on the synthetic
        mesh fallback, whose streets have no names to give."""
        if self.graph is not None:
            wp, _m, _s, names = self.graph.route_named(alat, alng, blat, blng, mode=mode)
            return wp, names
        wp = self.mesh.route(alat, alng, blat, blng)[0]
        return wp, [""] * len(wp)

    @staticmethod
    def _polyline_m(pts: list[tuple[float, float]]) -> float:
        return sum(geo.haversine_m(*a, *b) for a, b in zip(pts, pts[1:]))

    @staticmethod
    def _collapse_steps(waypoints: list[tuple[float, float]], names: list[str],
                        max_steps: int = 8) -> list[dict]:
        """Named waypoints -> compact turn-by-turn text: consecutive legs on
        the same street merge into one {street, m}; unnamed stretches (and
        the door-to-road approaches) read as "gali". Then keep absorbing the
        shortest step into its neighbor while any step is a <25 m connector
        stub or the list exceeds max_steps — approximate on purpose, this is
        a phone glanceable, not a survey. Metres are conserved throughout."""
        steps: list[dict] = []
        for prev, cur, nm in zip(waypoints, waypoints[1:], names[1:]):
            street = nm or "gali"
            d = geo.haversine_m(*prev, *cur)
            if steps and steps[-1]["street"] == street:
                steps[-1]["m"] += d
            else:
                steps.append({"street": street, "m": d})
        while len(steps) > 1:
            i = min(range(len(steps)), key=lambda k: steps[k]["m"])
            if steps[i]["m"] >= 25.0 and len(steps) <= max_steps:
                break
            j = i - 1 if i > 0 else 1
            steps[j]["m"] += steps.pop(i)["m"]
            merged: list[dict] = []       # absorbing can leave same-street twins
            for st in steps:
                if merged and merged[-1]["street"] == st["street"]:
                    merged[-1]["m"] += st["m"]
                else:
                    merged.append(st)
            steps = merged
        for st in steps:
            st["m"] = round(st["m"])
        return steps

    # ------------------------------------------------------------- depots --
    def _depot_stock(self, depot_id: str, sku: str) -> int:
        row = self.svc.store.one(
            "SELECT count FROM inventory WHERE partner_id=? AND sku=?", (depot_id, sku))
        return row["count"] if row else 0

    def _choose_depot(self, r: dict, sku: str, target: tuple[float, float]):
        """The cheapest-detour depot that still has the kit: minimizes
        road-distance(rider -> depot) + road-distance(depot -> case).
        Returns (depot_tuple, leg1, leg2) or None when every depot is dry."""
        best = None
        for depot in self.depot_list:
            if self._depot_stock(depot[0], sku) <= 0:
                continue
            leg1 = self._route_to(r, depot[2], depot[3])
            leg2 = self._route_between(r["mode"], depot[2], depot[3], *target)
            cost = self._polyline_m(leg1) + self._polyline_m(leg2)
            if best is None or cost < best[0]:
                best = (cost, depot, leg1, leg2)
        return None if best is None else best[1:]

    def depots(self) -> list[dict]:
        rows = self.svc.store.query("SELECT * FROM inventory")
        by_depot: dict[str, dict] = {}
        for row in rows:
            by_depot.setdefault(row["partner_id"], {})[row["sku"]] = row["count"]
        out = []
        for depot_id, name, lat, lng in self.depot_list:
            stock = by_depot.get(depot_id, {})
            low = [s for s, n in stock.items() if n <= 3]
            out.append({"id": depot_id, "name": name, "lat": lat, "lng": lng,
                        "stock": stock, "low": low})
        return out

    def restocks_view(self) -> list[dict]:
        """Couriers en route, for the coordinator's supply strip — the
        NGO head must see 'help is coming' next to the low-stock warning."""
        return [{"depot": self._depot_name(d), "sku": s,
                 "due_s": max(0, round(t - self.sim_now))}
                for (d, s), t in list(self._pending_restocks.items())]

    def _random_point(self, radius_frac: float = 1.0) -> tuple[float, float]:
        r = self.cfg.zone_radius_m * radius_frac * (self.rng.random() ** 0.5)
        ang = self.rng.uniform(0, 6.28318)
        lat, lng = geo.offset_m(self.cfg.zone_lat, self.cfg.zone_lng,
                                r * math.cos(ang), r * math.sin(ang))
        # Keep random spots near the street network. A point deep inside a
        # courtyard, park, or the rail yard forces a long straight approach
        # leg on every trip that touches it — riders visibly "fly" off-road.
        # Within 40 m of a road is believable (someone under a flyover isn't
        # standing ON the carriageway); beyond that, pull to the road edge.
        if self.graph is not None:
            snap = self.graph._snap(lat, lng, routing.SPEEDS_KMH["walk"])
            if snap is not None and snap.approach_m > 40:
                return snap.lat, snap.lng
        return lat, lng

    # ---------------------------------------------------------- scenarios --
    def run_scenario(self, name: str) -> str:
        if name == "golden_run":
            return self._golden_run()
        if name == "duplicate_burst":
            lat, lng = self._random_point(0.6)
            for _ in range(3):
                phone = self._next_phone()
                self._play(phone, [
                    ("text", "Ek aadmi ko chot lagi hai, patti se khoon aa raha hai"),
                    ("location_at", (lat + self.rng.uniform(-4e-4, 4e-4),
                                     lng + self.rng.uniform(-4e-4, 4e-4))),
                    ("button", "fresh:10"),
                ])
            return "3 witnesses reported the same spot"
        steps = SCENARIOS[name]
        phone = self._next_phone()
        self._play(phone, steps)
        self.last_scenario_phone = phone   # lets the UI jump to the thread
        return f"scenario {name} played"

    def _golden_run(self) -> str:
        """The video climax: a P1 medical case staged ~500m from a medical
        responder, who accepts wave 1, arrives, escalates to the clinical
        team, and the escalation completes — a guaranteed clean arc through
        the REAL pipeline (only the responder's dice are loaded)."""
        # Idle + non-manual only: hijacking a rider mid-job would strand
        # whatever they were doing (an onsite order has no other closer).
        med = next((r for r in self._resp.values()
                    if r["medical"] and r["state"] == "idle" and r.get("on_duty", True)
                    and r["id"] not in self.manual),
                   None)
        if med is None:
            return "no idle medical responder — try again in a moment"
        # Stage the pin CLEAR of every open case's dedup cell: if the report
        # merged into an existing case there'd be no fresh order, no loaded
        # dice — the "golden" run would just silently not be golden.
        lat = lng = None
        for _ in range(12):
            ang = self.rng.uniform(0, 6.28318)
            cand = geo.offset_m(med["lat"], med["lng"],
                                500 * math.cos(ang), 500 * math.sin(ang))
            if not self._near_open_case(*cand):
                lat, lng = cand
                break
        if lat is None:
            lat, lng = cand   # every bearing is busy — accept the merge risk
        phone = self._next_phone()
        self._play(phone, [
            ("text", "Flyover ke neeche aadmi ke pair mein gehri chot hai, purani patti lagi hai"),
            ("location_at", (lat, lng)),
            ("photo", "serious infected wound on foot, old dirty bandage, pus visible"),
            ("button", "fresh:10"),
        ])
        # Resolve the case through the conversation we just played — a global
        # "latest case" lookup can grab an unrelated case when the report
        # dedup-merges or ties on created_at.
        conv = self.svc.conversations.get(phone)
        case_id = conv.state.get("case_id") if conv else None
        order = (self.svc.store.one("SELECT * FROM orders WHERE case_id=? AND "
                                    "status IN ('queued', 'offered')", (case_id,))
                 if case_id else None)
        if order:
            self.golden[order["id"]] = med["id"]
            return f"golden run staged for {med['name']}"
        # Honest failure beats a fake success: the report merged or gated —
        # there is no fresh order, so no clean arc is coming.
        return ("golden report merged into an existing case — no clean arc; "
                "let nearby cases close and try again")

    def _near_open_case(self, lat: float, lng: float) -> bool:
        """Mirror the service's dedup query: would a report here merge?"""
        cells = geo.neighbor_keys(lat, lng, self.cfg.dedup_cell_m)
        marks = ",".join("?" for _ in cells)
        row = self.svc.store.one(
            f"SELECT id FROM cases WHERE status NOT IN ('closed') AND cell IN ({marks}) "
            f"AND created_at > ?",
            tuple(cells) + (self.sim_now - self.cfg.dedup_window_s,))
        return row is not None

    def _next_phone(self) -> str:
        self._phone_counter += 1
        return f"+91-9xx-{self._phone_counter:04d}"

    def _play(self, phone: str, steps: list) -> None:
        for kind, payload in steps:
            if kind == "text" or kind == "button":
                self.svc.wa_inbound(phone, kind, text=payload)
            elif kind == "photo":
                self.svc.wa_inbound(phone, "photo", photo_hint=payload)
            elif kind == "location":
                lat, lng = self._random_point(0.75)
                self.svc.wa_inbound(phone, "location", lat=lat, lng=lng)
            elif kind == "location_at":
                self.svc.wa_inbound(phone, "location", lat=payload[0], lng=payload[1])

    # --------------------------------------------------------------- tick --
    def tick(self, real_dt: float) -> None:
        self.last_tick_real = time.monotonic()   # heartbeat even while paused
        if not self.running:
            return
        with self._klock:
            self._tick_locked(real_dt)

    def _tick_locked(self, real_dt: float) -> None:
        dt = real_dt * self.speed
        self.sim_now += dt

        if self.sim_now >= self._random_report_at:
            self.run_scenario(self.rng.choice(["injured_flyover", "family_rain", "hungry_elder"]))
            self._random_report_at = self.sim_now + self.rng.uniform(300, 900)

        self.svc.dispatch.tick()
        self.svc.tick_recheck()
        self._sync_states()
        self._responders_decide()
        self._coordinator_plays()
        self._responders_move(dt)
        self._auto_pace()
        self._complete_escalations()
        self._process_restocks()
        # clock survives PUKAAR_DB restarts (see __init__)
        self.svc.store.execute(
            "INSERT OR REPLACE INTO push_meta (k, v) VALUES ('sim_now', ?)",
            (str(self.sim_now),))

    def _auto_pace(self) -> None:
        """Calm-board demo pacing: while a human-played rider is enroute,
        compress time so the audience never watches a dot walk for two real
        minutes; give the clock back the moment they arrive. The founder's
        own speed choice always wins — changing the speed dropdown clears
        the hold (api sim_ctl) instead of being clobbered on arrival."""
        if self.ambient:
            return
        travelling = any(r["state"] == "enroute" and r["id"] in self.manual
                         for r in self._resp.values())
        if travelling and self._pace_hold is None and self.speed < 24:
            self._pace_hold = self.speed
            self.speed = 24.0
            self.svc.emit("pace", {"on": True})
        elif not travelling and self._pace_hold is not None:
            self.speed = self._pace_hold
            self._pace_hold = None
            self.svc.emit("pace", {"on": False})

    def _coordinator_plays(self) -> None:
        """The human terminal rung, simulated: every ~90 sim-s the
        coordinator works the stuck backlog, assigning the oldest
        wave-exhausted orders to whoever is idle and nearest — exactly what
        the coordinator panel does by hand. (Without this, a load burst
        parks everything at needs_coordinator forever — found by the
        300-case test.)"""
        if self.sim_now < self._coord_next:
            return
        if not self.svc.dispatch.in_dispatch_window(self.sim_now):
            return  # the coordinator works the backlog inside partner hours
        self._coord_next = self.sim_now + 90
        stuck = self.svc.store.query(
            "SELECT * FROM orders WHERE status='needs_coordinator' ORDER BY created_at LIMIT 4")
        if not stuck:
            return
        used: set[str] = set()
        for order in stuck:
            case = self.svc.store.one("SELECT * FROM cases WHERE id=?", (order["case_id"],))
            if not case or case["lat"] is None:
                continue
            idle = [(geo.haversine_m(case["lat"], case["lng"], r["lat"], r["lng"]), r["id"])
                    for r in self._resp.values()
                    if r["state"] == "idle" and r.get("on_duty", True)
                    and r["id"] not in used and r["id"] not in self.manual]
            if not idle:
                return
            idle.sort()
            rid = idle[0][1]
            if self.svc.dispatch.manual_assign(order["id"], rid):
                used.add(rid)

    def _sync_states(self) -> None:
        """Reconcile kinetic state with order records — covers manual accepts,
        coordinator manual assigns, manual outcome closes from the UI, and
        orders recovered after a PUKAAR_DB restart."""
        for r in self._resp.values():
            if r["order_id"]:
                order = self.svc.store.one("SELECT * FROM orders WHERE id=?", (r["order_id"],))
                if not order or order["status"] in ("closed", "escalated"):
                    # Safety rail: every settling close path pops the
                    # reservation itself — one still present here means the
                    # order was closed externally without settling, i.e. the
                    # kit never reached anyone. Put it back on the shelf.
                    if order and r["order_id"] in self._reservations:
                        self.settle_kit(
                            r["order_id"],
                            "served" if order["status"] == "escalated" else "not_found")
                    r["state"], r["order_id"], r["target"] = "idle", None, None
                    r["route"], r["route_idx"], r["steps"] = None, 0, None
                    r["depot_id"], r["depot_name"] = None, None
                    r["pickup_idx"], r["picked_up"] = None, True
                    if not r.get("on_duty", True):
                        self.svc.positions.pop(r["id"], None)
            else:
                # 'onsite' included so a restart (or any external hiccup)
                # never strands a live order forever.
                order = self.svc.store.one(
                    "SELECT * FROM orders WHERE responder_id=? "
                    "AND status IN ('accepted', 'onsite')", (r["id"],))
                if order and order["status"] == "onsite":
                    case = self.svc.store.one(
                        "SELECT * FROM cases WHERE id=?", (order["case_id"],))
                    if case and case["lat"] is not None:
                        r["lat"], r["lng"] = case["lat"], case["lng"]
                    r["state"], r["order_id"] = "onsite", order["id"]
                    r["dwell_until"] = self.sim_now + self.rng.uniform(120, 300)
                elif order:
                    self._on_accept(r, order["id"])

    # ------------------------------------------------- responder behavior --
    def _responders_decide(self) -> None:
        pending = self.svc.store.query(
            "SELECT a.*, o.priority FROM assignments a JOIN orders o ON o.id = a.order_id "
            "WHERE a.responded_at IS NULL")
        # One decision timer PER OFFER. (A per-responder slot livelocks under
        # load: concurrent offers to the same responder keep resetting each
        # other's timer and nobody ever decides — found by the 300-case test.)
        live_ids = set()
        for a in pending:
            r = self._resp.get(a["responder_id"])
            if not r or a["responder_id"] in self.manual:
                continue  # a human is playing this responder from the UI
            golden_resp = self.golden.get(a["order_id"])
            if golden_resp and a["responder_id"] != golden_resp:
                self.svc.dispatch.respond(a["id"], False)   # scripted: others step back
                continue
            live_ids.add(a["id"])
            due = self._decides.get(a["id"])
            if due is None:
                delay = self.rng.uniform(15, 35) if golden_resp else self.rng.uniform(15, 90)
                self._decides[a["id"]] = self.sim_now + delay
                continue
            if self.sim_now >= due:
                if golden_resp:
                    # Loaded dice, real pipeline — but never hijack a live
                    # job; a decline degrades to needs_coordinator, which
                    # the coordinator rail already handles.
                    accepted = r["state"] == "idle" and r.get("on_duty", True)
                else:
                    p = r["accept_p"] * (1.25 if a["priority"] == "P1" else 1.0)
                    busy = r["state"] != "idle" or not r.get("on_duty", True)
                    accepted = (not busy) and self.rng.random() < min(0.95, p)
                if self.svc.dispatch.respond(a["id"], accepted) and accepted:
                    self._on_accept(r, a["order_id"])
                self._decides.pop(a["id"], None)
        # prune timers for offers that were answered/released elsewhere
        self._decides = {k: v for k, v in self._decides.items() if k in live_ids}

    def _on_accept(self, r: dict, order_id: str) -> None:
        case = self.svc.store.one(
            "SELECT c.* FROM cases c JOIN orders o ON o.case_id = c.id WHERE o.id=?", (order_id,))
        if not case or case["lat"] is None:
            return
        order = self.svc.store.one("SELECT * FROM orders WHERE id=?", (order_id,))
        target = (case["lat"], case["lng"])
        # Kits live at depots: route via the cheapest-detour depot that has
        # this SKU. A network-wide stockout goes direct + flags the
        # coordinator rather than stranding the case.
        already = self._reservations.get(order_id)
        if already:
            # Re-attach (restart, manual re-accept): the kit is already
            # reserved at a depot — route via THAT depot, don't re-reserve.
            depot = next((d for d in self.depot_list if d[0] == already[0]), None)
            pick = (depot,) if depot is not None else None
        else:
            pick = self._choose_depot(r, order["sku"], target) if order else None
        if pick:
            depot = pick[0]
            # Route the winning legs NAMED (A* is deterministic, so these are
            # the very polylines _choose_depot costed); names feed r["steps"].
            leg1, nm1 = self._route_named(r["mode"], r["lat"], r["lng"], depot[2], depot[3])
            leg2, nm2 = self._route_named(r["mode"], depot[2], depot[3], *target)
            waypoints, names = leg1 + leg2[1:], nm1 + nm2[1:]
            r["depot_id"], r["depot_name"] = depot[0], depot[1]
            r["pickup_idx"], r["picked_up"] = max(1, len(leg1) - 1), False
            if not already and order:
                # Reserve NOW: stock leaves the ledger at accept, so two
                # riders can never both be sent for the same last kit. A
                # not_found/declined outcome returns it (settle_kit).
                self._consume_kit(order["sku"], depot[0])
                self._reservations[order_id] = (depot[0], order["sku"])
                self._save_ledger()
        else:
            waypoints, names = self._route_named(r["mode"], r["lat"], r["lng"], *target)
            r["depot_id"], r["depot_name"] = None, None
            r["pickup_idx"], r["picked_up"] = None, True
            if order:
                self.svc.emit("coordinator_flag", {
                    "order_id": order_id,
                    "reason": f"stockout: no depot holds {order['sku']} — rider going direct"})
        r["state"], r["order_id"], r["target"] = "enroute", order_id, target
        # waypoints[0] is the responder's own current position — start at [1]
        r["route"], r["route_idx"] = waypoints, 1
        # Rider-facing turn-by-turn: compact named steps, plus the route's
        # total metres so the snapshot can place the current step cheaply.
        r["steps"] = self._collapse_steps(waypoints, names)
        r["_route_m"] = self._polyline_m(waypoints)
        # fresh safety clock: idle dwell before this job must not count as
        # "hasn't moved while en route"
        r["_last_pos"], r["_last_move_ts"] = None, self.sim_now

    def _advance_route(self, r: dict, dist_m: float) -> None:
        """Walk r along its mesh route by dist_m, waypoint by waypoint —
        never a straight beeline through whatever's between here and there."""
        route = r.get("route")
        if not route:
            # A mover without a polyline re-routes over the graph instead of
            # beelining through buildings; the straight step survives only as
            # the absolute last resort (no graph, no mesh — never in practice).
            r["route"], r["route_idx"] = self._route_to(r, *r["target"]), 1
            route = r.get("route")
            if not route:
                r["lat"], r["lng"] = geo.step_towards(r["lat"], r["lng"], *r["target"], dist_m)
                return
        remaining = dist_m
        while remaining > 0 and r["route_idx"] < len(route):
            nxt = route[r["route_idx"]]
            d = geo.haversine_m(r["lat"], r["lng"], *nxt)
            if d <= remaining:
                r["lat"], r["lng"] = nxt
                remaining -= d
                r["route_idx"] += 1
            else:
                r["lat"], r["lng"] = geo.step_towards(r["lat"], r["lng"], *nxt, remaining)
                remaining = 0.0
        # kit pickup: passing the depot waypoint flips the flag, once
        if (r["state"] == "enroute" and not r.get("picked_up")
                and r.get("pickup_idx") is not None and r["route_idx"] > r["pickup_idx"]):
            r["picked_up"] = True
            self.svc.emit("kit_pickup", {
                "responder_id": r["id"], "name": r["name"],
                "depot": r.get("depot_name"), "order_id": r.get("order_id")})

    def _check_overdue(self, r: dict) -> None:
        """Rider safety: an enroute responder whose position hasn't changed
        for 150+ sim-seconds gets flagged to the coordinator, once per
        order. Simulated riders always move — this fires for humans. The
        clock is reset at accept, so idle dwell never counts."""
        if r["state"] != "enroute":
            return
        pos = (round(r["lat"], 6), round(r["lng"], 6))
        moved = r.get("_last_pos") != pos
        if moved:
            r["_last_pos"], r["_last_move_ts"] = pos, self.sim_now
            return
        if (self.sim_now - r.get("_last_move_ts", self.sim_now) > 150
                and r.get("_overdue_for") != r["order_id"]):
            r["_overdue_for"] = r["order_id"]
            self.svc.emit("safety_alert", {
                "responder_id": r["id"], "name": r["name"], "order_id": r["order_id"],
                "reason": "no movement for 2½ min while en route — check in",
            })

    def _responders_move(self, dt: float) -> None:
        for r in self._resp.values():
            if not r.get("on_duty", True) and r["state"] == "idle":
                continue                     # off duty and free: not on the map
            self._check_overdue(r)
            if r["state"] == "enroute" and r["target"]:
                self._advance_route(r, r["speed"] * dt)
                # No arriving without the kit: if the route happens to pass
                # near the case BEFORE the depot, keep driving to the depot.
                if (r.get("picked_up", True)
                        and geo.haversine_m(r["lat"], r["lng"], *r["target"]) <= self.cfg.arrive_radius_m):
                    self.svc.dispatch.arrived(r["order_id"])
                    r["state"] = "onsite"
                    r["dwell_until"] = self.sim_now + self.rng.uniform(120, 300)
                    r["route"], r["route_idx"], r["steps"] = None, 0, None
            elif r["state"] == "onsite":
                if r["id"] not in self.manual and self.sim_now >= (r["dwell_until"] or 0):
                    self._close_order(r)
            elif self.ambient:  # idle drift — road-routed errands, ambient mode only
                if r["target"] is None or self.rng.random() < 0.005:
                    r["target"] = self._random_point()
                    r["route"], r["route_idx"] = self._route_to(r, *r["target"]), 1
                self._advance_route(r, r["speed"] * 0.4 * dt)
            # calm-mode idle: stand exactly where you are — a rider waits at
            # their spot until dispatch gives them a reason to move. The
            # guard keeps a just-closed off-duty rider from being re-added
            # the same tick _close_order removed them.
            if r.get("on_duty", True) or r["state"] != "idle":
                self.svc.positions[r["id"]] = (r["lat"], r["lng"])

    def _close_order(self, r: dict) -> None:
        order = self.svc.store.one("SELECT * FROM orders WHERE id=?", (r["order_id"],))
        if not order:
            r["state"], r["order_id"], r["target"] = "idle", None, None
            r["route"], r["route_idx"], r["steps"] = None, 0, None
            return
        if order["id"] in self.golden:
            outcome = "escalated"                # the arc the video needs, every time
        else:
            roll, acc = self.rng.random(), 0.0
            outcome = "served"
            for name, w in OUTCOME_WEIGHTS:
                acc += w
                if roll <= acc:
                    outcome = name
                    break
            if order["clinical_flag"] and outcome == "served" and self.rng.random() < 0.35:
                outcome = "escalated"
        closed = self.svc.dispatch.close(r["order_id"], outcome)
        if closed:
            self.settle_kit(order["id"], outcome)
            self.svc.notify_outcome(order["case_id"], outcome)
            if outcome == "escalated":
                due = 600 if order["id"] in self.golden else self.rng.uniform(600, 1500)
                self._pending_escalations[r["order_id"]] = self.sim_now + due
        r["state"], r["order_id"], r["target"] = "idle", None, None
        r["route"], r["route_idx"], r["steps"] = None, 0, None
        r["depot_id"], r["depot_name"], r["pickup_idx"], r["picked_up"] = None, None, None, True
        if not r.get("on_duty", True):     # off-duty request honored at close
            self.svc.positions.pop(r["id"], None)

    def settle_kit(self, order_id: str, outcome: str) -> None:
        """Settle an order's kit reservation on close — SHARED by the sim's
        auto-close and every external close path (responder app, supervisor
        UI). Stock left the depot at accept; a not_found/declined outcome
        puts it back, a served/escalated one keeps it consumed. RLock: safe
        both from inside the tick and from threadpool endpoints."""
        with self._klock:
            self._settle_kit_locked(order_id, outcome)

    def _settle_kit_locked(self, order_id: str, outcome: str) -> None:
        res = self._reservations.pop(order_id, None)
        if res:
            self._save_ledger()
        if res and outcome in ("not_found", "declined"):
            depot_id, sku = res
            self.svc.store.execute(
                "UPDATE inventory SET count = count + 1 WHERE partner_id=? AND sku=?",
                (depot_id, sku))
            self.svc.emit("kit_return", {"sku": sku, "depot": self._depot_name(depot_id)})

    def _save_ledger(self) -> None:
        """Reservations/restocks offset durable inventory rows — persist them
        beside the sim clock so a PUKAAR_DB restart reconciles (see __init__)."""
        self.svc.store.execute(
            "INSERT OR REPLACE INTO push_meta (k, v) VALUES ('kit_ledger', ?)",
            (json.dumps({
                "reservations": self._reservations,
                "restocks": {f"{d}|{s}": due
                             for (d, s), due in list(self._pending_restocks.items())},
            }),))

    # ------------------------------------------------- inventory & restock --
    def _depot_name(self, depot_id: str | None) -> str:
        return next((d[1] for d in self.depot_list if d[0] == depot_id), depot_id or "?")

    def _consume_kit(self, sku: str, depot_id: str | None = None) -> None:
        depot_id = depot_id or DEPOT_SEED[0][0]   # stockout fallback: book it somewhere honest
        self.svc.store.execute(
            "UPDATE inventory SET count = MAX(count - 1, 0) WHERE partner_id=? AND sku=?",
            (depot_id, sku))
        row = self.svc.store.one(
            "SELECT * FROM inventory WHERE partner_id=? AND sku=?", (depot_id, sku))
        key = (depot_id, sku)
        if row and row["count"] <= (row["restock_threshold"] or 0) and key not in self._restock_flagged:
            self._restock_flagged.add(key)
            self._pending_restocks[key] = self.sim_now + 600   # courier rail: ~10 sim-min
            self._save_ledger()   # an owed courier must survive a restart
            self.svc.emit("restock_needed", {"sku": sku, "count": row["count"],
                                             "depot": self._depot_name(depot_id)})

    def _process_restocks(self) -> None:
        done = [k for k, due in list(self._pending_restocks.items()) if self.sim_now >= due]
        for key in done:
            depot_id, sku = key
            self.svc.store.execute(
                "UPDATE inventory SET count = count + 8 WHERE partner_id=? AND sku=?",
                (depot_id, sku))
            del self._pending_restocks[key]
            self._restock_flagged.discard(key)
            self.svc.emit("restock_delivered", {"sku": sku, "qty": 8,
                                                "depot": self._depot_name(depot_id)})
        if done:
            self._save_ledger()

    def _complete_escalations(self) -> None:
        done = [oid for oid, t in list(self._pending_escalations.items()) if self.sim_now >= t]
        for oid in done:
            self.svc.dispatch.escalation_complete(oid)
            del self._pending_escalations[oid]

    # ---------------------------------------------------------- demo seed --
    def seed_demo(self) -> None:
        """Pre-stage a photogenic session (PUKAAR_SEED_DEMO=1 / `make demo`):
        one case already served in history, one mid-flight, and a golden run
        just accepted — recordable within seconds of boot. Also seeds the
        90-day aggregate cells so the privacy heatmap has history to show:
        coarse cell + count is ALL that survives the purge, which is the point."""
        self.speed = 12.0
        hotspots = [self._random_point(0.9) for _ in range(9)]
        for _ in range(26):
            lat, lng = self.rng.choice(hotspots)
            self.svc.store.execute(
                "INSERT INTO analytics_cells (cell, category, n) VALUES (?, ?, 1) "
                "ON CONFLICT(cell, category) DO UPDATE SET n = n + 1",
                (geo.cell_key(lat, lng),
                 self.rng.choice(["medical", "food", "food", "shelter"])))
        # Trips are longer now that riders travel real streets at real
        # per-mode speeds AND detour via a kit depot — the first staged case
        # needs a wider window to reach a closed outcome before boot.
        self.run_scenario("hungry_elder")
        self._fast_forward(2100)
        self.run_scenario("family_rain")
        self._fast_forward(240)
        self.run_scenario("golden_run")
        self._fast_forward(200)

    def _fast_forward(self, sim_seconds: float, step: float = 5.0) -> None:
        t = 0.0
        while t < sim_seconds:
            self.tick(step / self.speed)
            t += step

    # ------------------------------------------------------------ snapshot --
    def snapshot(self) -> dict:
        return {
            "sim_now": self.sim_now,
            "clock": self._clock_str(),
            "speed": self.speed,
            "running": self.running,
            "is_night": not self.svc.dispatch.in_dispatch_window(self.sim_now),
            "golden": list(self.golden.keys()),
            "responders": [self._responder_view(r) for r in self._resp.values()],
        }

    def _responder_view(self, r: dict) -> dict:
        route_out, eta_s, dist_m, step_i = None, None, None, None
        steps = r.get("steps")
        if r["state"] == "enroute" and r.get("route"):
            route_out = [[lat, lng] for lat, lng in r["route"][r["route_idx"]:]]
            dist_m = round(routing.route_remaining_m(r["route"], r["route_idx"], r["lat"], r["lng"]))
            eta_s = round(dist_m / r["speed"]) if r["speed"] > 0 else None
            if steps:
                # Current step ≈ where (total - remaining) lands on the
                # cumulative step metres — cheap, and plenty for a highlight
                # that refreshes every poll anyway.
                covered = max(0.0, r.get("_route_m", 0.0) - dist_m)
                step_i, acc = len(steps) - 1, 0.0
                for i, st in enumerate(steps):
                    acc += st["m"]
                    if covered < acc:
                        step_i = i
                        break
        return {
            "id": r["id"], "name": r["name"], "medical": r["medical"], "mode": r["mode"],
            "lat": r["lat"], "lng": r["lng"], "state": r["state"], "order_id": r["order_id"],
            "manual": r["id"] in self.manual, "route": route_out, "eta_s": eta_s, "dist_m": dist_m,
            "depot": r.get("depot_name"), "picked_up": bool(r.get("picked_up", True)),
            "steps": steps, "step_i": step_i, "on_duty": bool(r.get("on_duty", True)),
        }

    def _clock_str(self) -> str:
        day = int(self.sim_now // 86400)
        h = int(self.sim_now % 86400 // 3600)
        m = int(self.sim_now % 3600 // 60)
        return f"Day {day} · {h:02d}:{m:02d}"
