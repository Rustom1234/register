"""PukaarService — wires the whole loop together.

inbound message -> gate -> intake -> (dedup) case -> route -> order ->
dispatch -> outcome -> closure message. Also owns conversations, the
event feed, metrics, and provenance signing.
"""

from __future__ import annotations

import hashlib
import statistics
from collections import deque

from . import geo, digipin, strings
from .backends import make_backend
from .config import Config
from .db import Store, new_id
from .dispatch import DispatchEngine
from .intake import BotMsg, Conversation, Intake
from .orders import build_order, route
from .provenance import Provenance
from .retention import purge


class PukaarService:
    def __init__(self, cfg: Config, store: Store, now_fn):
        self.cfg = cfg
        self.store = store
        self.now = now_fn
        self.backend = make_backend(cfg)
        self.prov = Provenance(cfg.hmac_key or None)
        self.intake = Intake(self.backend)
        self.conversations: dict[str, Conversation] = {}
        self.feed: deque[dict] = deque(maxlen=250)
        self.positions: dict[str, tuple[float, float]] = {}
        self.dispatch = DispatchEngine(store, cfg, now_fn, lambda: self.positions, self.emit)

    # ------------------------------------------------------------- feed --
    def emit(self, kind: str, data: dict) -> None:
        self.feed.append({"ts": self.now(), "kind": kind, **data})

    # ---------------------------------------------------------- inbound --
    def wa_inbound(self, phone: str, kind: str, text: str | None = None,
                   lat: float | None = None, lng: float | None = None,
                   photo_hint: str | None = None) -> list[BotMsg]:
        phone_hash = hashlib.sha256(f"pukaar:{phone}".encode()).hexdigest()[:12]
        conv = self.conversations.setdefault(phone, Conversation(phone_hash=phone_hash))
        shown = text if kind != "location" else "📍 location"
        conv.remember("witness", kind, shown or kind, ts=self.now())

        replies = self.intake.handle(conv, kind, text=text, lat=lat, lng=lng, photo_hint=photo_hint)

        if conv.state["stage"] == "emergency_redirect":
            self.emit("emergency_redirect", {"phone_hash": phone_hash})
            self._record_report(conv, kind, shown, case_id=None)
            conv.state["stage"] = "need_location"  # allow a normal report after
        elif conv.state.get("ready_case"):
            case_payload = conv.state.pop("ready_case")
            case = self._create_or_merge_case(case_payload, conv)
            conv.state["case_id"] = case["id"]
            self._record_report(conv, kind, shown, case_id=case["id"])
            replies.append(BotMsg(strings.fmt("S-EXPECT", case_id=case["id"][-4:].upper()),
                                  string_id="S-EXPECT"))
        else:
            self._record_report(conv, kind, shown, case_id=conv.state.get("case_id"))

        for r in replies:
            conv.remember("bot", "text", r.text, r.buttons, ts=self.now())
        return replies

    def _record_report(self, conv: Conversation, kind: str, body: str | None, case_id: str | None) -> None:
        payload = {"kind": kind, "body": body or "", "case_id": case_id}
        self.store.insert("reports", {
            "id": new_id("rep"), "case_id": case_id, "reporter_hash": conv.phone_hash,
            "lang": "hi-en", "body": body, "media_ref": "media" if kind == "photo" else None,
            "media_purged": 0, "received_at": self.now(), "provenance": "witness",
            "hmac": self.prov.sign("witness", payload),
        })

    # ------------------------------------------------------------- cases --
    def _create_or_merge_case(self, p: dict, conv: Conversation) -> dict:
        now = self.now()
        if p["lat"] is not None:
            cell = geo.cell_key(p["lat"], p["lng"], self.cfg.dedup_cell_m)
            neighbors = geo.neighbor_keys(p["lat"], p["lng"], self.cfg.dedup_cell_m)
            marks = ",".join("?" for _ in neighbors)
            existing = self.store.one(
                f"SELECT * FROM cases WHERE status NOT IN ('closed') AND cell IN ({marks}) "
                f"AND created_at > ? ORDER BY created_at DESC",
                tuple(neighbors) + (now - self.cfg.dedup_window_s,))
            if existing:
                self.store.update("cases", existing["id"],
                                  {"merged_witnesses": existing["merged_witnesses"] + 1})
                self.emit("case_merged", {"case_id": existing["id"],
                                          "witnesses": existing["merged_witnesses"] + 1})
                return existing
        else:
            cell = "landmark"

        case = {
            "id": new_id("case"), "status": "new", "category": p["category"],
            "category_conf": p["category_conf"], "urgency": p.get("urgency", "medium"),
            "cell": cell, "lat": p["lat"], "lng": p["lng"], "geo_conf": p["geo_conf"],
            "landmark_text": p["landmark_text"], "freshness_min": p["freshness_min"],
            "detail": p["detail"], "merged_witnesses": 1,
            "created_at": now, "closed_at": None, "expires_at": now + 72 * 3600,
        }
        self.store.insert("cases", case)
        self.emit("case_created", {"case_id": case["id"], "category": case["category"],
                                   "lat": case["lat"], "lng": case["lng"]})

        routing = route(case, self.backend)
        order = build_order(case, routing, self.backend)
        if order["priority"] == "P1":
            self.store.update("cases", case["id"], {"urgency": "high"})
        mac = self.prov.sign("agent_inferred", {k: order[k] for k in ("sku", "priority", "clinical_flag")})
        self.dispatch.create_order(case, order, mac)
        self.store.update("cases", case["id"], {"status": "routed"})
        return case

    # ------------------------------------------------------------ closure --
    def notify_outcome(self, case_id: str, outcome: str) -> None:
        sid = {"served": "S-CLOSURE-SERVED", "escalated": "S-CLOSURE-ESCALATED",
               "not_found": "S-CLOSURE-NOTFOUND", "declined": "S-CLOSURE-DECLINED"}[outcome]
        for conv in self.conversations.values():
            if conv.state.get("case_id") == case_id and not conv.state["stopped"]:
                msg = strings.fmt(sid, case_id=case_id[-4:].upper())
                conv.remember("bot", "text", msg, ts=self.now())

    # ------------------------------------------------------------ metrics --
    def metrics(self) -> dict:
        q = self.store.query
        open_cases = q("SELECT COUNT(*) n FROM cases WHERE status NOT IN ('closed')")[0]["n"]
        served = q("SELECT COUNT(*) n FROM outcomes WHERE served=1")[0]["n"]
        escalated = q("SELECT COUNT(*) n FROM outcomes WHERE escalated=1")[0]["n"]
        # Order-level acceptance (GoodSAM's "% of alerts accepted"): an order
        # counts once no matter how many parallel offers its waves fanned out.
        offers = q("SELECT COUNT(DISTINCT order_id) n FROM assignments")[0]["n"]
        accepts = q("SELECT COUNT(*) n FROM orders WHERE accepted_at IS NOT NULL")[0]["n"]
        accept_times = [r["accepted_at"] - r["created_at"] for r in
                        q("SELECT created_at, accepted_at FROM orders WHERE accepted_at IS NOT NULL")]
        kits = {r["sku"]: r["count"] for r in q("SELECT sku, count FROM inventory WHERE partner_id='partner_1'")}
        return {
            "open_cases": open_cases,
            "served": served,
            "escalated": escalated,
            "acceptance_pct": round(100 * accepts / offers) if offers else None,
            "median_accept_s": round(statistics.median(accept_times)) if accept_times else None,
            "p90_accept_s": (round(sorted(accept_times)[max(0, int(len(accept_times) * 0.9) - 1)])
                             if accept_times else None),
            "kits": kits,
        }

    # -------------------------------------------------------------- misc --
    def run_purge(self) -> dict:
        stats = purge(self.store, self.cfg, self.now())
        self.emit("purge", stats)
        return stats

    def digipin_for(self, lat: float | None, lng: float | None) -> str | None:
        if lat is None or lng is None:
            return None
        try:
            return digipin.encode(lat, lng)
        except ValueError:
            return None
