"""PukaarService — wires the whole loop together.

inbound message -> gate -> intake -> (dedup) case -> route -> order ->
dispatch -> outcome -> closure message. Also owns conversations, the
event feed, metrics, and provenance signing.
"""

from __future__ import annotations

import hashlib
import re
import statistics
from collections import deque

_DEVA_RX = re.compile(r"[ऀ-ॿ]")
_HINGLISH_RX = re.compile(
    r"\b(hai|hain|nahi|nahin|mein|bhaiya|aadmi|aurat|amma|raha|rahi|rahe|karo|karein|"
    r"chahiye|paas|neeche|upar|wala|gaya|gayi|bhookh|bhooke|thand|khoon|patti|ghayal|"
    r"madad|jaldi|abhi|dekha|bahut|zaroorat|baarish|bheeg|kambal|pada|leti|uth)\b", re.I)
_ASCII_WORD_RX = re.compile(r"[a-zA-Z]{2,}")


def detect_lang(text: str | None) -> str | None:
    """Mirror the witness: Devanagari script -> deva; Hindi words in Latin
    script -> hinglish; plain English -> en; unknown -> None (keep prior)."""
    if not text:
        return None
    if _DEVA_RX.search(text):
        return "deva"
    if _HINGLISH_RX.search(text):
        return "hinglish"
    if _ASCII_WORD_RX.search(text):
        return "en"
    return None

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
        # Witness-facing language: "auto" mirrors each witness's own language
        # (en / hinglish / deva); a fixed value overrides for all replies.
        self.script = "auto"
        self.conversations: dict[str, Conversation] = {}
        self.feed: deque[dict] = deque(maxlen=250)
        self.positions: dict[str, tuple[float, float]] = {}
        self.dispatch = DispatchEngine(store, cfg, now_fn, lambda: self.positions, self.emit)

    # ------------------------------------------------------------- feed --
    def emit(self, kind: str, data: dict) -> None:
        self.feed.append({"ts": self.now(), "kind": kind, **data})

    def lang_for(self, conv: Conversation) -> str:
        if self.script != "auto":
            return self.script
        return conv.state.get("lang", "hinglish")

    # ---------------------------------------------------------- inbound --
    def wa_inbound(self, phone: str, kind: str, text: str | None = None,
                   lat: float | None = None, lng: float | None = None,
                   photo_hint: str | None = None) -> list[BotMsg]:
        phone_hash = hashlib.sha256(f"pukaar:{phone}".encode()).hexdigest()[:12]
        conv = self.conversations.setdefault(phone, Conversation(phone_hash=phone_hash))
        if kind == "location":
            shown = "📍 location"
        elif kind == "voice":
            shown = f"🎤 {text}" if text else "🎤 (voice note)"
        else:
            shown = text
        conv.remember("witness", kind, shown or kind, ts=self.now())
        if kind in ("text", "voice"):
            detected = detect_lang(text)
            if detected:
                conv.state["lang"] = detected
        lang = self.lang_for(conv)

        # Voice notes carry a transcript (demo: canned; P1: Sarvam STT) and
        # flow through intake exactly like text.
        intake_kind = "text" if kind == "voice" else kind
        replies = self.intake.handle(conv, intake_kind, text=text, lat=lat, lng=lng, photo_hint=photo_hint)
        for r in replies:  # localize fixed strings to the witness's language
            if r.string_id in strings.SAFETY and "{" not in strings.SAFETY[r.string_id]:
                r.text = strings.text(r.string_id, lang)
                r.buttons = strings.localized_buttons(r.buttons, lang)

        if conv.state["stage"] == "emergency_redirect":
            self.emit("emergency_redirect", {"phone_hash": phone_hash})
            self._record_report(conv, kind, shown, case_id=None)
            conv.state["stage"] = "need_location"  # allow a normal report after
        elif conv.state.get("ready_case"):
            case_payload = conv.state.pop("ready_case")
            case = self._create_or_merge_case(case_payload, conv)
            conv.state["case_id"] = case["id"]
            self._record_report(conv, kind, shown, case_id=case["id"])
            if self.dispatch.in_dispatch_window():
                replies.append(BotMsg(strings.fmt("S-EXPECT", lang, case_id=case["id"][-4:].upper()),
                                      string_id="S-EXPECT"))
            else:
                self.emit("night_hold", {"case_id": case["id"]})
                replies.append(BotMsg(strings.fmt("S-EXPECT-NIGHT", lang, case_id=case["id"][-4:].upper()),
                                      string_id="S-EXPECT-NIGHT"))
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
                msg = strings.fmt(sid, self.lang_for(conv), case_id=case_id[-4:].upper())
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
        inv = q("SELECT sku, count, restock_threshold FROM inventory WHERE partner_id='partner_1'")
        kits = {r["sku"]: r["count"] for r in inv}
        kits_low = [r["sku"] for r in inv if r["count"] <= (r["restock_threshold"] or 0)]
        return {
            "open_cases": open_cases,
            "served": served,
            "escalated": escalated,
            "acceptance_pct": round(100 * accepts / offers) if offers else None,
            "median_accept_s": round(statistics.median(accept_times)) if accept_times else None,
            "p90_accept_s": (round(sorted(accept_times)[max(0, int(len(accept_times) * 0.9) - 1)])
                             if accept_times else None),
            "kits": kits,
            "kits_low": kits_low,
        }

    def daily_metrics(self) -> dict:
        """Per-sim-day aggregates + kill-criteria evaluation (build plan §7).
        Cost model: kit ₹300 + ₹120 per dispatch run (research cost basis)."""
        q = self.store.query
        days: dict[int, dict] = {}

        def day_of(ts: float) -> int:
            return int(ts // 86400)

        def bucket(d: int) -> dict:
            return days.setdefault(d, {
                "day": d, "cases": 0, "by_category": {"medical": 0, "food": 0, "shelter": 0},
                "served": 0, "escalated": 0, "not_found": 0, "declined": 0,
                "offers": 0, "accepts": 0, "arrivals": 0,
            })

        for c in q("SELECT created_at, category FROM cases"):
            b = bucket(day_of(c["created_at"]))
            b["cases"] += 1
            if c["category"] in b["by_category"]:
                b["by_category"][c["category"]] += 1
        for o in q("SELECT * FROM outcomes"):
            b = bucket(day_of(o["created_at"]))
            if o["escalated"]:
                b["escalated"] += 1
            elif o["served"]:
                b["served"] += 1
            elif not o["found"]:
                b["not_found"] += 1
            else:
                b["declined"] += 1
        for o in q("SELECT created_at, accepted_at, arrived_at FROM orders"):
            if o["accepted_at"] is not None:
                bucket(day_of(o["accepted_at"]))["accepts"] += 1
            if o["arrived_at"] is not None:
                bucket(day_of(o["arrived_at"]))["arrivals"] += 1
        for r in q("SELECT MIN(offered_at) t FROM assignments GROUP BY order_id"):
            bucket(day_of(r["t"]))["offers"] += 1

        m = self.metrics()
        outs = q("SELECT * FROM outcomes")
        found = sum(1 for o in outs if o["found"])
        served_total = sum(1 for o in outs if o["served"])
        arrivals_total = q("SELECT COUNT(*) n FROM orders WHERE arrived_at IS NOT NULL")[0]["n"]
        cost_total = served_total * 420 + max(0, arrivals_total - served_total) * 120
        cost_per_served = round(cost_total / served_total) if served_total else None
        kill = [
            {"name": "Verified-need rate (found/closed)", "value": round(100 * found / len(outs)) if outs else None,
             "target": ">= 40%", "ok": (found / len(outs) >= 0.4) if outs else None},
            {"name": "Offer acceptance", "value": m["acceptance_pct"],
             "target": ">= 50%", "ok": (m["acceptance_pct"] >= 50) if m["acceptance_pct"] is not None else None},
            {"name": "Cost per person served", "value": cost_per_served,
             "target": "<= ₹900 (3× kit)", "ok": (cost_per_served <= 900) if cost_per_served else None},
            {"name": "Open backlog", "value": m["open_cases"],
             "target": "<= 12 (capacity)", "ok": m["open_cases"] <= 12},
        ]
        return {"days": [days[d] for d in sorted(days)], "kill": kill,
                "totals": {"served": served_total, "cost_total": cost_total}}

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
