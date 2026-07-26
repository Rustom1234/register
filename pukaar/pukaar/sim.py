"""Simulation engine — makes the demo alive without real people.

Responders move through the pilot zone on a sim clock (config.sim_speed
sim-seconds per real second), receive offers from the real dispatch
engine, accept with GoodSAM-informed probabilities, travel, and close
cases with realistic outcome mixes. Witness scenarios drive the REAL
intake pipeline — nothing in the demo bypasses the production code path.
"""

from __future__ import annotations

import random

from . import geo
from .config import Config
from .db import new_id
from .service import PukaarService

RESPONDER_SEED = [
    ("Meena", True), ("Arjun", False), ("Fatima", True),
    ("Ravi", False), ("Sunita", False), ("Imran", False),
]

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
        self.sim_now = 8 * 3600.0          # 08:00 sim time, day 0
        self.running = True
        self.speed = cfg.sim_speed
        self.manual: set[str] = set()      # responders a human is playing via the UI
        self.golden: dict[str, str] = {}   # order_id -> chosen responder (scripted clean arc)
        self._restock_flagged: set[str] = set()
        self._pending_restocks: dict[str, float] = {}   # sku -> delivery due (sim ts)
        self._phone_counter = 0
        self._resp: dict[str, dict] = {}
        self._pending_escalations: dict[str, float] = {}
        self._random_report_at = self.sim_now + self.rng.uniform(60, 240)
        self._seed_world()

    # -------------------------------------------------------------- setup --
    def _seed_world(self) -> None:
        for sku, count in (("MED-1", 18), ("FOOD-1", 24), ("SEAS-M", 15)):
            self.svc.store.execute(
                "INSERT OR REPLACE INTO inventory (partner_id, sku, count, restock_threshold) "
                "VALUES ('partner_1', ?, ?, 6)", (sku, count))
        for i, (name, medical) in enumerate(RESPONDER_SEED):
            rid = f"resp_{i+1}"
            self.svc.store.insert("responders", {
                "id": rid, "partner_id": "partner_1", "display_name": name,
                "medical": int(medical), "vetting": "verified", "active": 1,
            })
            lat, lng = self._random_point(0.85)
            self._resp[rid] = {
                "id": rid, "name": name, "medical": medical, "lat": lat, "lng": lng,
                "speed": self.rng.uniform(3.5, 5.5),          # m per sim-second (~cycle)
                "accept_p": self.rng.uniform(0.55, 0.85),      # GoodSAM band, generous end
                "state": "idle", "order_id": None, "target": None,
                "decide_at": None, "dwell_until": None,
            }
            self.svc.positions[rid] = (lat, lng)

    def _random_point(self, radius_frac: float = 1.0) -> tuple[float, float]:
        r = self.cfg.zone_radius_m * radius_frac * (self.rng.random() ** 0.5)
        ang = self.rng.uniform(0, 6.28318)
        import math
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
        import math
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
        case = self.svc.store.one("SELECT * FROM cases ORDER BY created_at DESC")
        order = self.svc.store.one("SELECT * FROM orders WHERE case_id=?", (case["id"],)) if case else None
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
        if not self.running:
            return
        dt = real_dt * self.speed
        self.sim_now += dt

        if self.sim_now >= self._random_report_at:
            self.run_scenario(self.rng.choice(["injured_flyover", "family_rain", "hungry_elder"]))
            self._random_report_at = self.sim_now + self.rng.uniform(300, 900)

        self.svc.dispatch.tick()
        self._sync_states()
        self._responders_decide()
        self._responders_move(dt)
        self._complete_escalations()
        self._process_restocks()

    def _sync_states(self) -> None:
        """Reconcile kinetic state with order records — covers manual accepts,
        coordinator manual assigns, and manual outcome closes from the UI."""
        for r in self._resp.values():
            if r["order_id"]:
                order = self.svc.store.one("SELECT * FROM orders WHERE id=?", (r["order_id"],))
                if not order or order["status"] in ("closed", "escalated"):
                    r["state"], r["order_id"], r["target"] = "idle", None, None
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
        for a in pending:
            r = self._resp.get(a["responder_id"])
            if not r or a["responder_id"] in self.manual:
                continue  # a human is playing this responder from the UI
            golden_resp = self.golden.get(a["order_id"])
            if golden_resp and a["responder_id"] != golden_resp:
                self.svc.dispatch.respond(a["id"], False)   # scripted: others step back
                continue
            key = a["id"]
            if r["decide_at"] is None or r.get("decide_key") != key:
                delay = self.rng.uniform(15, 35) if golden_resp else self.rng.uniform(15, 90)
                r["decide_at"] = self.sim_now + delay
                r["decide_key"] = key
                continue
            if self.sim_now >= r["decide_at"]:
                if golden_resp:
                    accepted = True                          # loaded dice, real pipeline
                else:
                    p = r["accept_p"] * (1.25 if a["priority"] == "P1" else 1.0)
                    busy = r["state"] != "idle"
                    accepted = (not busy) and self.rng.random() < min(0.95, p)
                if self.svc.dispatch.respond(a["id"], accepted) and accepted:
                    self._on_accept(r, a["order_id"])
                r["decide_at"], r["decide_key"] = None, None

    def _on_accept(self, r: dict, order_id: str) -> None:
        case = self.svc.store.one(
            "SELECT c.* FROM cases c JOIN orders o ON o.case_id = c.id WHERE o.id=?", (order_id,))
        if not case or case["lat"] is None:
            return
        r["state"], r["order_id"], r["target"] = "enroute", order_id, (case["lat"], case["lng"])

    def _responders_move(self, dt: float) -> None:
        for r in self._resp.values():
            if r["state"] == "enroute" and r["target"]:
                r["lat"], r["lng"] = geo.step_towards(r["lat"], r["lng"], *r["target"], r["speed"] * dt)
                if geo.haversine_m(r["lat"], r["lng"], *r["target"]) <= self.cfg.arrive_radius_m:
                    self.svc.dispatch.arrived(r["order_id"])
                    r["state"] = "onsite"
                    r["dwell_until"] = self.sim_now + self.rng.uniform(120, 300)
            elif r["state"] == "onsite":
                if r["id"] not in self.manual and self.sim_now >= (r["dwell_until"] or 0):
                    self._close_order(r)
            else:  # idle drift
                if r["target"] is None or self.rng.random() < 0.005:
                    r["target"] = self._random_point()
                r["lat"], r["lng"] = geo.step_towards(r["lat"], r["lng"], *r["target"], r["speed"] * 0.4 * dt)
            self.svc.positions[r["id"]] = (r["lat"], r["lng"])

    def _close_order(self, r: dict) -> None:
        order = self.svc.store.one("SELECT * FROM orders WHERE id=?", (r["order_id"],))
        if not order:
            r["state"], r["order_id"], r["target"] = "idle", None, None
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
                self._consume_kit(order["sku"])
            self.svc.notify_outcome(order["case_id"], outcome)
            if outcome == "escalated":
                due = 600 if order["id"] in self.golden else self.rng.uniform(600, 1500)
                self._pending_escalations[r["order_id"]] = self.sim_now + due
        r["state"], r["order_id"], r["target"] = "idle", None, None

    # ------------------------------------------------- inventory & restock --
    def _consume_kit(self, sku: str) -> None:
        self.svc.store.execute(
            "UPDATE inventory SET count = MAX(count - 1, 0) WHERE partner_id='partner_1' AND sku=?",
            (sku,))
        row = self.svc.store.one(
            "SELECT * FROM inventory WHERE partner_id='partner_1' AND sku=?", (sku,))
        if row and row["count"] <= (row["restock_threshold"] or 0) and sku not in self._restock_flagged:
            self._restock_flagged.add(sku)
            self._pending_restocks[sku] = self.sim_now + 600   # courier rail: ~10 sim-min
            self.svc.emit("restock_needed", {"sku": sku, "count": row["count"]})

    def _process_restocks(self) -> None:
        done = [sku for sku, due in self._pending_restocks.items() if self.sim_now >= due]
        for sku in done:
            self.svc.store.execute(
                "UPDATE inventory SET count = count + 12 WHERE partner_id='partner_1' AND sku=?", (sku,))
            del self._pending_restocks[sku]
            self._restock_flagged.discard(sku)
            self.svc.emit("restock_delivered", {"sku": sku, "qty": 12})

    def _complete_escalations(self) -> None:
        done = [oid for oid, t in self._pending_escalations.items() if self.sim_now >= t]
        for oid in done:
            self.svc.dispatch.escalation_complete(oid)
            del self._pending_escalations[oid]

    # ------------------------------------------------------------ snapshot --
    def snapshot(self) -> dict:
        return {
            "sim_now": self.sim_now,
            "clock": self._clock_str(),
            "speed": self.speed,
            "running": self.running,
            "is_night": not self.svc.dispatch.in_dispatch_window(self.sim_now),
            "responders": [
                {"id": r["id"], "name": r["name"], "medical": r["medical"],
                 "lat": r["lat"], "lng": r["lng"], "state": r["state"], "order_id": r["order_id"],
                 "manual": r["id"] in self.manual}
                for r in self._resp.values()
            ],
        }

    def _clock_str(self) -> str:
        day = int(self.sim_now // 86400)
        h = int(self.sim_now % 86400 // 3600)
        m = int(self.sim_now % 3600 // 60)
        return f"Day {day} · {h:02d}:{m:02d}"
