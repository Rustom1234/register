"""Dispatch engine — the GoodSAM-shaped parallel wave (build plan §3.9).

Parallel offer to the k nearest on-shift responders (k=3 for P1, else 2),
first accept locks (a compare-and-swap on the order row), 3-minute waves,
<=3 waves, then the human coordinator is the terminal rung — inside the
07:00-21:00 dispatch window. A wave that expires overnight re-queues the
order for the morning round (night timeouts stay wave-eligible).
Tick-driven with an injected clock so tests and the simulator control
time; no threads, no sleeps.
"""

from __future__ import annotations

from typing import Callable

from . import geo
from .config import Config
from .db import Store, new_id


class DispatchEngine:
    def __init__(self, store: Store, cfg: Config, now_fn: Callable[[], float],
                 positions_fn: Callable[[], dict[str, tuple[float, float]]],
                 on_event: Callable[[str, dict], None]):
        self.store = store
        self.cfg = cfg
        self.now = now_fn
        self.positions = positions_fn      # live responder positions from the sim
        self.emit = on_event               # feed events for the UI / audit trail

    # ------------------------------------------------------------- create
    def create_order(self, case: dict, order: dict, mac: str) -> dict:
        row = {
            "id": new_id("ord"), "case_id": case["id"], "sku": order["sku"],
            "addons": order["addons"], "clinical_flag": int(order["clinical_flag"]),
            "priority": order["priority"], "instruction_ids": order["instruction_ids"],
            "partner_id": "partner_1", "status": "queued",
            "created_by": order["created_by"], "confidence": order["confidence"],
            "wave": 0, "responder_id": None, "created_at": self.now(),
            "accepted_at": None, "arrived_at": None, "closed_at": None, "hmac": mac,
        }
        self.store.insert("orders", row)
        self.store.audit("dispatch", "order_created", row["id"], "agent_inferred", mac,
                         f"{order['sku']} {order['priority']}", ts=self.now())
        self.emit("order_created", {"order_id": row["id"], "case_id": case["id"],
                                    "priority": order["priority"], "sku": order["sku"],
                                    "clinical_flag": order["clinical_flag"]})
        if order.get("needs_review"):
            self.emit("coordinator_flag", {"order_id": row["id"], "reason": "low-confidence routing"})
        return row

    # --------------------------------------------------------------- tick
    def in_dispatch_window(self, now: float | None = None) -> bool:
        hour = int(((now if now is not None else self.now()) % 86400) // 3600)
        return self.cfg.dispatch_open_h <= hour < self.cfg.dispatch_close_h

    def tick(self) -> None:
        now = self.now()
        if self.in_dispatch_window(now):
            for order in self.store.query("SELECT * FROM orders WHERE status='queued'"):
                self._start_wave(order, wave=1)
        for order in self.store.query("SELECT * FROM orders WHERE status='offered'"):
            self._check_wave(order, now)

    # ------------------------------------------------------------ waves --
    def _candidates(self, order: dict, exclude: set[str], k: int) -> list[str]:
        case = self.store.one("SELECT * FROM cases WHERE id=?", (order["case_id"],))
        if not case or case["lat"] is None:
            return []
        open_counts: dict[str, int] = {}
        for r in self.store.query(
                "SELECT responder_id, COUNT(*) n FROM orders WHERE status IN ('accepted','onsite') GROUP BY responder_id"):
            open_counts[r["responder_id"]] = r["n"]
        cands = []
        for rid, (lat, lng) in self.positions().items():
            row = self.store.one("SELECT * FROM responders WHERE id=? AND active=1", (rid,))
            if not row or rid in exclude:
                continue
            if open_counts.get(rid, 0) >= self.cfg.responder_open_cap:
                continue
            cands.append((geo.haversine_m(case["lat"], case["lng"], lat, lng), rid))
        cands.sort()
        return [rid for _, rid in cands[:k]]

    def _start_wave(self, order: dict, wave: int) -> None:
        already = {a["responder_id"] for a in
                   self.store.query("SELECT responder_id FROM assignments WHERE order_id=? "
                                    "AND (response IS NULL OR response != 'timeout_night')",
                                    (order["id"],))}
        k = self.cfg.wave_size_p1 if order["priority"] == "P1" else self.cfg.wave_size_default
        cands = self._candidates(order, already, k)
        if not cands:
            self._to_coordinator(order, "no responders available")
            return
        now = self.now()
        for rid in cands:
            self.store.insert("assignments", {
                "id": new_id("asg"), "order_id": order["id"], "responder_id": rid,
                "offered_at": now, "responded_at": None, "response": None,
            })
        self.store.update("orders", order["id"], {"status": "offered", "wave": wave})
        self.emit("wave_started", {"order_id": order["id"], "wave": wave, "offered_to": cands,
                                   "priority": order["priority"], "sku": order["sku"]})
        if order["priority"] == "P1" and wave == 1:
            self.emit("coordinator_flag", {"order_id": order["id"], "reason": "P1 dispatched — watch"})

    def _check_wave(self, order: dict, now: float) -> None:
        asgs = self.store.query(
            "SELECT * FROM assignments WHERE order_id=? AND responded_at IS NULL", (order["id"],))
        live = [a for a in asgs if now - a["offered_at"] <= self.cfg.offer_ttl_s]
        if asgs and not live:
            for a in asgs:  # expire the wave
                self.store.update("assignments", a["id"], {"responded_at": now, "response": "timeout"})
            asgs = []
        if not asgs:  # declined/timed out -> overnight requeue / next wave / coordinator
            if not self.in_dispatch_window(now):
                # No fresh offers outside 07:00-21:00: park the order back in
                # the queue; the morning tick re-waves it inside the window.
                # A night timeout is not a decline — those responders stay
                # eligible for the morning round.
                self.store.execute(
                    "UPDATE assignments SET response='timeout_night' "
                    "WHERE order_id=? AND response='timeout'", (order["id"],))
                self.store.update("orders", order["id"], {"status": "queued"})
                self.store.audit("dispatch", "requeued_overnight", order["id"], "system",
                                 "", "wave expired outside dispatch window", ts=now)
                return
            if order["wave"] >= self.cfg.max_waves:
                self._to_coordinator(order, "all waves exhausted")
            else:
                self._start_wave(order, order["wave"] + 1)

    def _to_coordinator(self, order: dict, reason: str) -> None:
        self.store.update("orders", order["id"], {"status": "needs_coordinator"})
        self.store.audit("dispatch", "coordinator_escalation", order["id"], "system", "", reason, ts=self.now())
        self.emit("coordinator_alert", {"order_id": order["id"], "reason": reason})

    def manual_assign(self, order_id: str, responder_id: str) -> bool:
        """Coordinator override: hand a stuck order to a chosen responder.
        Refuses pinless (landmark-only) cases — get a pin first — and yields
        if a responder accept wins the compare-and-swap concurrently.
        Recorded as an assignment like any other, provenance actor = human."""
        order = self.store.one("SELECT * FROM orders WHERE id=?", (order_id,))
        resp = self.store.one("SELECT * FROM responders WHERE id=? AND active=1", (responder_id,))
        if not order or not resp or order["status"] not in ("needs_coordinator", "queued", "offered"):
            return False
        case = self.store.one("SELECT * FROM cases WHERE id=?", (order["case_id"],))
        if not case or case["lat"] is None:
            # Landmark-only case: nowhere to navigate to. The coordinator must
            # get a pin (call the witness) before this order can be assigned —
            # otherwise the responder would be locked to an unreachable job.
            return False
        now = self.now()
        won = self.store.claim(
            "UPDATE orders SET status='accepted', responder_id=?, accepted_at=? "
            "WHERE id=? AND status IN ('needs_coordinator', 'queued', 'offered')",
            (responder_id, now, order_id))
        if not won:  # a responder accepted concurrently — their lock stands
            return False
        for other in self.store.query(
                "SELECT * FROM assignments WHERE order_id=? AND responded_at IS NULL", (order_id,)):
            self.store.update("assignments", other["id"], {"responded_at": now, "response": "released"})
        self.store.insert("assignments", {
            "id": new_id("asg"), "order_id": order_id, "responder_id": responder_id,
            "offered_at": now, "responded_at": now, "response": "accepted",
        })
        self.store.audit("coordinator", "manual_assign", order_id, "system", "", responder_id, ts=now)
        self.emit("manual_assign", {"order_id": order_id, "responder_id": responder_id})
        return True

    # ------------------------------------------------- responder actions --
    def respond(self, assignment_id: str, accepted: bool) -> bool:
        """First accept locks the order; everyone else is released.
        The lock is a compare-and-swap on the order row, so two concurrent
        accepts (HTTP threadpool + sim tick) can never both win."""
        a = self.store.one("SELECT * FROM assignments WHERE id=?", (assignment_id,))
        if not a or a["responded_at"] is not None:
            return False
        now = self.now()
        order = self.store.one("SELECT * FROM orders WHERE id=?", (a["order_id"],))
        if not order or order["status"] not in ("offered",):
            self.store.update("assignments", assignment_id, {"responded_at": now, "response": "released"})
            return False
        if not accepted:
            self.store.update("assignments", assignment_id, {"responded_at": now, "response": "declined"})
            return True
        won = self.store.claim(
            "UPDATE orders SET status='accepted', responder_id=?, accepted_at=? "
            "WHERE id=? AND status='offered'",
            (a["responder_id"], now, order["id"]))
        if not won:  # someone else accepted between our read and this write
            self.store.update("assignments", assignment_id, {"responded_at": now, "response": "released"})
            return False
        self.store.update("assignments", assignment_id, {"responded_at": now, "response": "accepted"})
        for other in self.store.query(
                "SELECT * FROM assignments WHERE order_id=? AND responded_at IS NULL", (order["id"],)):
            self.store.update("assignments", other["id"], {"responded_at": now, "response": "released"})
        self.emit("order_accepted", {"order_id": order["id"], "responder_id": a["responder_id"],
                                     "wave": order["wave"], "accept_s": now - a["offered_at"]})
        return True

    def arrived(self, order_id: str) -> None:
        order = self.store.one("SELECT * FROM orders WHERE id=?", (order_id,))
        if order and order["status"] == "accepted":
            self.store.update("orders", order_id, {"status": "onsite", "arrived_at": self.now()})
            self.emit("responder_arrived", {"order_id": order_id, "responder_id": order["responder_id"]})

    def close(self, order_id: str, outcome: str) -> dict | None:
        """outcome in: served | not_found | declined | escalated."""
        order = self.store.one("SELECT * FROM orders WHERE id=?", (order_id,))
        if not order or order["status"] not in ("onsite", "accepted", "needs_coordinator"):
            return None
        now = self.now()
        status = "escalated" if outcome == "escalated" else "closed"
        self.store.update("orders", order_id, {"status": status, "closed_at": now})
        self.store.insert("outcomes", {
            "id": new_id("out"), "case_id": order["case_id"],
            "found": int(outcome != "not_found"), "served": int(outcome in ("served", "escalated")),
            "person_accepted": int(outcome in ("served", "escalated")),
            "escalated": int(outcome == "escalated"), "escalation_completed_at": None,
            "closed_by": order["responder_id"] or "coordinator", "created_at": now,
        })
        case_status = "escalated" if outcome == "escalated" else "closed"
        self.store.update("cases", order["case_id"], {"status": case_status,
                                                      "closed_at": None if outcome == "escalated" else now})
        self.store.audit(order["responder_id"] or "coordinator", f"outcome_{outcome}",
                         order["case_id"], "responder_observed", "", ts=now)
        self.emit("outcome", {"order_id": order_id, "case_id": order["case_id"], "outcome": outcome})
        return order

    def cancel(self, order_id: str, reason: str) -> bool:
        """Close an order without a visit (e.g., the witness says the person
        has moved on). Pending offers are released; the outcome records
        found=0 so the verified-need metric stays honest."""
        order = self.store.one("SELECT * FROM orders WHERE id=?", (order_id,))
        if not order or order["status"] in ("closed", "escalated"):
            return False
        now = self.now()
        for a in self.store.query(
                "SELECT * FROM assignments WHERE order_id=? AND responded_at IS NULL", (order_id,)):
            self.store.update("assignments", a["id"], {"responded_at": now, "response": "released"})
        self.store.update("orders", order_id, {"status": "closed", "closed_at": now})
        self.store.insert("outcomes", {
            "id": new_id("out"), "case_id": order["case_id"], "found": 0, "served": 0,
            "person_accepted": 0, "escalated": 0, "escalation_completed_at": None,
            "closed_by": "witness", "created_at": now,
        })
        self.store.update("cases", order["case_id"], {"status": "closed", "closed_at": now})
        self.store.audit("witness", "case_withdrawn", order["case_id"], "witness", "", reason, ts=now)
        self.emit("case_withdrawn", {"order_id": order_id, "case_id": order["case_id"], "reason": reason})
        return True

    def escalation_complete(self, order_id: str) -> None:
        order = self.store.one("SELECT * FROM orders WHERE id=?", (order_id,))
        if not order or order["status"] != "escalated":
            return
        now = self.now()
        self.store.update("orders", order_id, {"status": "closed"})
        self.store.update("cases", order["case_id"], {"status": "closed", "closed_at": now})
        self.store.execute(
            "UPDATE outcomes SET escalation_completed_at=? WHERE case_id=? AND escalated=1",
            (now, order["case_id"]))
        self.emit("escalation_complete", {"order_id": order_id, "case_id": order["case_id"]})
