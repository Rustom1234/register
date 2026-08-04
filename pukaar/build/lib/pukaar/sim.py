"""Simulation engine — makes the demo alive without real people.

Responders move through the pilot zone on a sim clock (config.sim_speed
sim-seconds per real second), receive offers from the real dispatch
engine, accept with GoodSAM-informed probabilities, travel, and close
cases with realistic outcome mixes. Witness scenarios drive the REAL
intake pipeline — nothing in the demo bypasses the production code path.
"""

from __future__ import annotations

import math
import random
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
        self.running = True
        self.speed = cfg.sim_speed
        self.manual: set[str] = set()      # responders a human is playing via the UI
        self.golden: dict[str, str] = {}   # order_id -> chosen responder (scripted clean arc)
        self._restock_flagged: set[tuple[str, str]] = set()          # (depot, sku)
        self._pending_restocks: dict[tuple[str, str], float] = {}    # (depot, sku) -> due
        self._phone_counter = 0
        self._resp: dict[str, dict] = {}
        self._decides: dict[str, float] = {}   # assignment_id -> decision due (per-offer, not per-responder)
        self._coord_next = 0.0                 # the sim plays the coordinator too
        self._pending_escalations: dict[str, float] = {}
        self._random_report_at = self.sim_now + self.rng.uniform(60, 240)
        self.last_tick_real = time.monotonic()   # /health watchdog signal
        self._seed_world()

    # -------------------------------------------------------------- setup --
    def _seed_world(self) -> None:
        # Stock lives at depots (inventory.partner_id carries the depot id).
        for depot_id, stock in DEPOT_STOCK_SEED.items():
            for sku, count in stock.items():
                self.svc.store.execute(
                    "INSERT OR REPLACE INTO inventory (partner_id, sku, count, restock_threshold) "
                    "VALUES (?, ?, ?, 3)", (depot_id, sku, count))
        for i, (name, medical, mode) in enumerate(RESPONDER_SEED):
            rid = f"resp_{i+1}"
            self.svc.store.insert("responders", {
                "id": rid, "partner_id": "partner_1", "display_name": name,
                "medical": int(medical), "vetting": "verified", "active": 1,
            })
            lat, lng = self._random_point(0.85)
            self._resp[rid] = {
                "id": rid, "name": name, "medical": medical, "lat": lat, "lng": lng,
                "mode": mode, "speed": MODE_SPEED_MPS[mode],   # m per sim-second
                "accept_p": self.rng.uniform(0.55, 0.85),      # GoodSAM band, generous end
                "state": "idle", "order_id": None, "target": None,
                "dwell_until": None, "route": None, "route_idx": 0,
                "depot_id": None, "depot_name": None, "pickup_idx": None, "picked_up": True,
            }
            self.svc.positions[rid] = (lat, lng)

    def _route_to(self, r: dict, tlat: float, tlng: float) -> list[tuple[float, float]]:
        """Waypoints for r to reach (tlat, tlng) by its travel mode, over
        the real road graph when available."""
        return self._route_between(r["mode"], r["lat"], r["lng"], tlat, tlng)

    def _route_between(self, mode: str, alat: float, alng: float,
                       blat: float, blng: float) -> list[tuple[float, float]]:
        if self.graph is not None:
            return self.graph.route(alat, alng, blat, blng, mode=mode)[0]
        return self.mesh.route(alat, alng, blat, blng)[0]

    @staticmethod
    def _polyline_m(pts: list[tuple[float, float]]) -> float:
        return sum(geo.haversine_m(*a, *b) for a, b in zip(pts, pts[1:]))

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

    def _random_point(self, radius_frac: float = 1.0) -> tuple[float, float]:
        r = self.cfg.zone_radius_m * radius_frac * (self.rng.random() ** 0.5)
        ang = self.rng.uniform(0, 6.28318)
        return geo.offset_m(self.cfg.zone_lat, self.cfg.zone_lng,
                            r * math.cos(ang), r * math.sin(ang))

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
        self._play(self._next_phone(), steps)
        return f"scenario {name} played"

    def _golden_run(self) -> str:
        """The video climax: a P1 medical case staged ~500m from a medical
        responder, who accepts wave 1, arrives, escalates to the clinical
        team, and the escalation completes — a guaranteed clean arc through
        the REAL pipeline (only the responder's dice are loaded)."""
        med = next((r for r in self._resp.values() if r["medical"]), None)
        if med is None:
            return "no medical responder available"
        ang = self.rng.uniform(0, 6.28318)
        lat, lng = geo.offset_m(med["lat"], med["lng"],
                                500 * math.cos(ang), 500 * math.sin(ang))
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
        self._complete_escalations()
        self._process_restocks()

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
                    if r["state"] == "idle" and r["id"] not in used and r["id"] not in self.manual]
            if not idle:
                return
            idle.sort()
            rid = idle[0][1]
            if self.svc.dispatch.manual_assign(order["id"], rid):
                used.add(rid)

    def _sync_states(self) -> None:
        """Reconcile kinetic state with order records — covers manual accepts,
        coordinator manual assigns, and manual outcome closes from the UI."""
        for r in self._resp.values():
            if r["order_id"]:
                order = self.svc.store.one("SELECT * FROM orders WHERE id=?", (r["order_id"],))
                if not order or order["status"] in ("closed", "escalated"):
                    r["state"], r["order_id"], r["target"] = "idle", None, None
                    r["route"], r["route_idx"] = None, 0
            else:
                order = self.svc.store.one(
                    "SELECT * FROM orders WHERE responder_id=? AND status='accepted'", (r["id"],))
                if order:
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
                    accepted = True                          # loaded dice, real pipeline
                else:
                    p = r["accept_p"] * (1.25 if a["priority"] == "P1" else 1.0)
                    busy = r["state"] != "idle"
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
        pick = self._choose_depot(r, order["sku"], target) if order else None
        if pick:
            depot, leg1, leg2 = pick
            waypoints = leg1 + leg2[1:]
            r["depot_id"], r["depot_name"] = depot[0], depot[1]
            r["pickup_idx"], r["picked_up"] = max(1, len(leg1) - 1), False
        else:
            waypoints = self._route_to(r, *target)
            r["depot_id"], r["depot_name"] = None, None
            r["pickup_idx"], r["picked_up"] = None, True
            if order:
                self.svc.emit("coordinator_flag", {
                    "order_id": order_id,
                    "reason": f"stockout: no depot holds {order['sku']} — rider going direct"})
        r["state"], r["order_id"], r["target"] = "enroute", order_id, target
        # waypoints[0] is the responder's own current position — start at [1]
        r["route"], r["route_idx"] = waypoints, 1
        # fresh safety clock: idle dwell before this job must not count as
        # "hasn't moved while en route"
        r["_last_pos"], r["_last_move_ts"] = None, self.sim_now

    def _advance_route(self, r: dict, dist_m: float) -> None:
        """Walk r along its mesh route by dist_m, waypoint by waypoint —
        never a straight beeline through whatever's between here and there."""
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
            self._check_overdue(r)
            if r["state"] == "enroute" and r["target"]:
                self._advance_route(r, r["speed"] * dt)
                if geo.haversine_m(r["lat"], r["lng"], *r["target"]) <= self.cfg.arrive_radius_m:
                    self.svc.dispatch.arrived(r["order_id"])
                    r["state"] = "onsite"
                    r["dwell_until"] = self.sim_now + self.rng.uniform(120, 300)
                    r["route"], r["route_idx"] = None, 0
            elif r["state"] == "onsite":
                if r["id"] not in self.manual and self.sim_now >= (r["dwell_until"] or 0):
                    self._close_order(r)
            else:  # idle drift — still road-routed, just slower and ambient
                if r["target"] is None or self.rng.random() < 0.005:
                    r["target"] = self._random_point()
                    r["route"], r["route_idx"] = self._route_to(r, *r["target"]), 1
                self._advance_route(r, r["speed"] * 0.4 * dt)
            self.svc.positions[r["id"]] = (r["lat"], r["lng"])

    def _close_order(self, r: dict) -> None:
        order = self.svc.store.one("SELECT * FROM orders WHERE id=?", (r["order_id"],))
        if not order:
            r["state"], r["order_id"], r["target"] = "idle", None, None
            r["route"], r["route_idx"] = None, 0
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
            if outcome in ("served", "escalated"):
                self._consume_kit(order["sku"], r.get("depot_id"))
            self.svc.notify_outcome(order["case_id"], outcome)
            if outcome == "escalated":
                due = 600 if order["id"] in self.golden else self.rng.uniform(600, 1500)
                self._pending_escalations[r["order_id"]] = self.sim_now + due
        r["state"], r["order_id"], r["target"] = "idle", None, None
        r["route"], r["route_idx"] = None, 0
        r["depot_id"], r["depot_name"], r["pickup_idx"], r["picked_up"] = None, None, None, True

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
            self.svc.emit("restock_needed", {"sku": sku, "count": row["count"],
                                             "depot": self._depot_name(depot_id)})

    def _process_restocks(self) -> None:
        done = [k for k, due in self._pending_restocks.items() if self.sim_now >= due]
        for key in done:
            depot_id, sku = key
            self.svc.store.execute(
                "UPDATE inventory SET count = count + 8 WHERE partner_id=? AND sku=?",
                (depot_id, sku))
            del self._pending_restocks[key]
            self._restock_flagged.discard(key)
            self.svc.emit("restock_delivered", {"sku": sku, "qty": 8,
                                                "depot": self._depot_name(depot_id)})

    def _complete_escalations(self) -> None:
        done = [oid for oid, t in self._pending_escalations.items() if self.sim_now >= t]
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
        route_out, eta_s, dist_m = None, None, None
        if r["state"] == "enroute" and r.get("route"):
            route_out = [[lat, lng] for lat, lng in r["route"][r["route_idx"]:]]
            dist_m = round(routing.route_remaining_m(r["route"], r["route_idx"], r["lat"], r["lng"]))
            eta_s = round(dist_m / r["speed"]) if r["speed"] > 0 else None
        return {
            "id": r["id"], "name": r["name"], "medical": r["medical"], "mode": r["mode"],
            "lat": r["lat"], "lng": r["lng"], "state": r["state"], "order_id": r["order_id"],
            "manual": r["id"] in self.manual, "route": route_out, "eta_s": eta_s, "dist_m": dist_m,
            "depot": r.get("depot_name"), "picked_up": bool(r.get("picked_up", True)),
        }

    def _clock_str(self) -> str:
        day = int(self.sim_now // 86400)
        h = int(self.sim_now % 86400 // 3600)
        m = int(self.sim_now % 3600 // 60)
        return f"Day {day} · {h:02d}:{m:02d}"
