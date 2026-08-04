"""PukaarService — wires the whole loop together.

inbound message -> gate -> intake -> (dedup) case -> route -> order ->
dispatch -> outcome -> closure message. Also owns conversations, the
event feed, metrics, and provenance signing.
"""

from __future__ import annotations

import hashlib
import json
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

from . import digipin, gate, geo, strings
from .backends import make_backend
from .config import Config
from .db import Store, new_id
from .dispatch import DispatchEngine
from .intake import BotMsg, Conversation, Intake
from .orders import build_order, route
from .provenance import Provenance
from .push import PushService
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
        self._msg_times: dict[str, deque] = {}   # phone -> recent inbound ts
        self.dispatch = DispatchEngine(store, cfg, now_fn, lambda: self.positions, self.emit)
        self.push = PushService(store)
        self._load_conversations()

    # ------------------------------------------------------- persistence --
    # Conversations survive restarts (risk register #8): a witness mid-intake
    # picks up where they left off instead of being stranded silently.
    def _load_conversations(self) -> None:
        for row in self.store.query("SELECT * FROM conversations"):
            conv = Conversation(phone_hash=row["phone_hash"])
            try:
                conv.state.update(json.loads(row["state"]))
                conv.log = json.loads(row["log"])
            except (TypeError, ValueError):
                continue  # corrupt row -> that witness simply starts fresh
            self.conversations[row["phone"]] = conv

    def _save_conversation(self, phone: str, conv: Conversation) -> None:
        self.store.insert("conversations", {
            "phone": phone, "phone_hash": conv.phone_hash,
            "state": conv.state, "log": conv.log[-60:],
            "updated_at": self.now(),
        })

    # ------------------------------------------------------------- feed --
    def emit(self, kind: str, data: dict) -> None:
        self.feed.append({"ts": self.now(), "kind": kind, **data})
        # Witness progress updates ride the same dispatch events the feed
        # shows — the witness loop closes tighter than closure-only.
        if kind in ("order_accepted", "manual_assign"):
            self._notify_progress(data.get("order_id"), "S-PROGRESS-ACCEPTED",
                                  data.get("responder_id"))
        elif kind == "responder_arrived":
            self._notify_progress(data.get("order_id"), "S-PROGRESS-ARRIVED",
                                  data.get("responder_id"))
        elif kind == "wave_started":
            # The offer ping reaches the phone even with the app closed.
            for rid in data.get("offered_to", []):
                self.push.notify(rid, "Wayside — new offer",
                                 f"{data.get('sku', 'kit')} nearby · first accept wins")

    def _notify_progress(self, order_id: str | None, sid: str, responder_id: str | None) -> None:
        if not order_id:
            return
        order = self.store.one("SELECT * FROM orders WHERE id=?", (order_id,))
        if not order:
            return
        resp = self.store.one("SELECT * FROM responders WHERE id=?", (responder_id,)) if responder_id else None
        name = (resp or {}).get("display_name") or "karyakarta"
        case_id = order["case_id"]
        for phone, conv in list(self.conversations.items()):
            if conv.state.get("case_id") == case_id and not conv.state["stopped"]:
                msg = strings.fmt(sid, self.lang_for(conv),
                                  case_id=case_id[-4:].upper(), name=name)
                conv.remember("bot", "text", msg, ts=self.now())
                self._save_conversation(phone, conv)

    def lang_for(self, conv: Conversation) -> str:
        if self.script != "auto":
            return self.script
        return conv.state.get("lang", "hinglish")

    # ---------------------------------------------------------- inbound --
    def wa_inbound(self, phone: str, kind: str, text: str | None = None,
                   lat: float | None = None, lng: float | None = None,
                   photo_hint: str | None = None,
                   media_ref: str | None = None) -> list[BotMsg]:
        phone_hash = hashlib.sha256(f"pukaar:{phone}".encode()).hexdigest()[:12]
        conv = self.conversations.setdefault(phone, Conversation(phone_hash=phone_hash))

        # Abuse guard: a per-witness message budget. Emergencies bypass it —
        # the gate's fixed reply is cheap and a life is not (risk #5/#15).
        now = self.now()
        times = self._msg_times.setdefault(phone, deque())
        while times and now - times[0] > self.cfg.rate_limit_window_s:
            times.popleft()
        if len(times) >= self.cfg.rate_limit_msgs and not (kind == "text" and gate.is_emergency(text)):
            if len(times) == self.cfg.rate_limit_msgs:   # say it once, then silence
                times.append(now)
                msg = strings.text("S-SLOWDOWN", self.lang_for(conv))
                conv.remember("bot", "text", msg, ts=now)
                self._save_conversation(phone, conv)
                return [BotMsg(msg, string_id="S-SLOWDOWN")]
            return []
        times.append(now)

        if kind == "location":
            shown = "📍 location"
        elif kind == "photo":
            shown = "📷 photo"
        elif kind == "voice":
            shown = f"🎤 {text}" if text else "🎤 (voice note)"
        elif kind == "button":
            # Log the human label, not the wire ID (still:yes → "Haan, wahin hai").
            shown = strings.button_label(text or "", self.lang_for(conv)) or text
        else:
            shown = text
        conv.remember("witness", kind, shown or kind, ts=self.now())
        if kind in ("text", "voice"):
            detected = detect_lang(text)
            if detected:
                conv.state["lang"] = detected
        lang = self.lang_for(conv)

        # A pin the coordinator asked for lands on the EXISTING case — it
        # must not open a new report (risk #13: landmark-only cases).
        if kind == "location" and lat is not None and conv.state.get("await_pin_case"):
            cid = conv.state.pop("await_pin_case")
            case = self.store.one(
                "SELECT * FROM cases WHERE id=? AND status NOT IN ('closed','escalated')", (cid,))
            if case and case["lat"] is None:
                self.store.update("cases", cid, {
                    "lat": lat, "lng": lng, "geo_conf": "pin",
                    "cell": geo.cell_key(lat, lng, self.cfg.dedup_cell_m)})
                order = self.store.one(
                    "SELECT * FROM orders WHERE case_id=? AND status='needs_coordinator'", (cid,))
                if order:
                    self.store.update("orders", order["id"], {"status": "queued"})
                self.emit("pin_received", {"case_id": cid})
                msg = strings.fmt("S-PIN-THANKS", lang, case_id=cid[-4:].upper())
                conv.remember("bot", "text", msg, ts=self.now())
                self._save_conversation(phone, conv)
                return [BotMsg(msg, string_id="S-PIN-THANKS")]

        # Voice notes carry a transcript (demo: canned; P1: Sarvam STT) and
        # flow through intake exactly like text.
        intake_kind = "text" if kind == "voice" else kind
        replies = self.intake.handle(conv, intake_kind, text=text, lat=lat, lng=lng, photo_hint=photo_hint)
        for r in replies:  # localize fixed strings to the witness's language
            if r.string_id in strings.SAFETY and "{" not in strings.SAFETY[r.string_id]:
                r.text = strings.text(r.string_id, lang)
                r.buttons = strings.localized_buttons(r.buttons, lang)

        reply = conv.state.pop("_recheck_reply", None)
        if reply is not None:
            self._handle_recheck_reply(conv, reply)
        if conv.state["stage"] == "emergency_redirect":
            self.emit("emergency_redirect", {"phone_hash": phone_hash})
            self._record_report(conv, kind, shown, case_id=None, media_ref=media_ref)
            conv.state["stage"] = "need_location"  # allow a normal report after
        elif conv.state.get("ready_case"):
            case_payload = conv.state.pop("ready_case")
            case = self._create_or_merge_case(case_payload, conv)
            conv.state["case_id"] = case["id"]
            self._record_report(conv, kind, shown, case_id=case["id"], media_ref=media_ref)
            # Retro-link this witness's pre-case media: photos usually arrive
            # BEFORE the pin completes the case — without this they'd stay
            # orphaned and invisible to the ops room (and to retention's
            # case-close deletion) forever.
            self.store.execute(
                "UPDATE reports SET case_id=? WHERE reporter_hash=? AND case_id IS NULL "
                "AND media_ref IS NOT NULL AND received_at > ?",
                (case["id"], conv.phone_hash, self.now() - 3600))
            if self.dispatch.in_dispatch_window():
                replies.append(BotMsg(strings.fmt("S-EXPECT", lang, case_id=case["id"][-4:].upper()),
                                      string_id="S-EXPECT"))
            else:
                self.emit("night_hold", {"case_id": case["id"]})
                replies.append(BotMsg(strings.fmt("S-EXPECT-NIGHT", lang, case_id=case["id"][-4:].upper()),
                                      string_id="S-EXPECT-NIGHT"))
        else:
            self._record_report(conv, kind, shown, case_id=conv.state.get("case_id"), media_ref=media_ref)

        for r in replies:
            conv.remember("bot", "text", r.text, r.buttons, ts=self.now())
        self._save_conversation(phone, conv)
        return replies

    def _record_report(self, conv: Conversation, kind: str, body: str | None,
                       case_id: str | None, media_ref: str | None = None) -> None:
        payload = {"kind": kind, "body": body or "", "case_id": case_id}
        # media_ref: a real uploaded filename when the witness sent an actual
        # photo; the historical "media" placeholder for described photos.
        self.store.insert("reports", {
            "id": new_id("rep"), "case_id": case_id, "reporter_hash": conv.phone_hash,
            "lang": "hi-en", "body": body,
            "media_ref": media_ref or ("media" if kind == "photo" else None),
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

    # ---------------------------------------------------------- re-check --
    def tick_recheck(self) -> None:
        """Stale-pin defense (StreetLink's 36% never-located): a case still
        unserved past the threshold asks its witness — once — whether the
        person is still there. Yes refreshes; no closes honestly."""
        now = self.now()
        stale = self.store.query(
            "SELECT c.* FROM cases c JOIN orders o ON o.case_id = c.id "
            "WHERE c.recheck_sent=0 AND c.status NOT IN ('closed','escalated') "
            "AND o.status IN ('queued','offered','needs_coordinator') AND c.created_at < ?",
            (now - self.cfg.recheck_after_s,))
        for case in stale:
            found = next(((p, c) for p, c in list(self.conversations.items())
                          if c.state.get("case_id") == case["id"] and not c.state["stopped"]), None)
            self.store.update("cases", case["id"], {"recheck_sent": 1})
            if not found:
                continue
            phone, conv = found
            lang = self.lang_for(conv)
            msg = strings.fmt("S-STILLTHERE", lang, case_id=case["id"][-4:].upper())
            buttons = strings.localized_buttons(list(strings.STILL_BUTTONS), lang)
            conv.remember("bot", "text", msg, buttons, ts=now)
            self._save_conversation(phone, conv)
            self.emit("recheck_sent", {"case_id": case["id"]})

    def _handle_recheck_reply(self, conv, answer: str) -> None:
        case_id = conv.state.get("case_id")
        if not case_id:
            return
        case = self.store.one("SELECT * FROM cases WHERE id=?", (case_id,))
        if not case or case["status"] in ("closed", "escalated"):
            return
        if answer == "yes":
            self.store.update("cases", case_id, {"freshness_min": 0})
            self.emit("recheck_confirmed", {"case_id": case_id})
        else:
            order = self.store.one("SELECT * FROM orders WHERE case_id=?", (case_id,))
            if order and self.dispatch.cancel(order["id"], "witness says person moved on"):
                # The rider may already be enroute with a reserved kit — the
                # person is gone, so the kit goes back on the shelf. The sim
                # registers this hook at boot (service can't import sim).
                settle = getattr(self, "kit_settler", None)
                if settle:
                    settle(order["id"], "not_found")

    def request_pin(self, case_id: str) -> bool:
        """Coordinator one-tap: ask the witness of a landmark-only case for
        an exact pin. The next location they share updates THIS case."""
        case = self.store.one("SELECT * FROM cases WHERE id=?", (case_id,))
        if not case or case["lat"] is not None:
            return False
        found = next(((p, c) for p, c in list(self.conversations.items())
                      if c.state.get("case_id") == case_id and not c.state["stopped"]), None)
        if not found:
            return False
        phone, conv = found
        conv.state["await_pin_case"] = case_id
        msg = strings.fmt("S-PIN-PLEASE", self.lang_for(conv), case_id=case_id[-4:].upper())
        conv.remember("bot", "text", msg, ts=self.now())
        self._save_conversation(phone, conv)
        self.emit("pin_requested", {"case_id": case_id})
        return True

    # ------------------------------------------------------------ closure --
    def notify_outcome(self, case_id: str, outcome: str) -> None:
        sid = {"served": "S-CLOSURE-SERVED", "escalated": "S-CLOSURE-ESCALATED",
               "not_found": "S-CLOSURE-NOTFOUND", "declined": "S-CLOSURE-DECLINED"}[outcome]
        for phone, conv in list(self.conversations.items()):
            if conv.state.get("case_id") == case_id and not conv.state["stopped"]:
                msg = strings.fmt(sid, self.lang_for(conv), case_id=case_id[-4:].upper())
                conv.remember("bot", "text", msg, ts=self.now())
                self._save_conversation(phone, conv)

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
        # Stock is held per depot (inventory.partner_id = depot id); the
        # headline tile shows the network total, the map shows each depot.
        inv = q("SELECT sku, SUM(count) AS count, MIN(restock_threshold) AS restock_threshold "
                "FROM inventory GROUP BY sku")
        kits = {r["sku"]: r["count"] for r in inv}
        low_rows = q("SELECT DISTINCT sku FROM inventory "
                     "WHERE count <= COALESCE(restock_threshold, 0)")
        kits_low = [r["sku"] for r in low_rows]
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

    def shift_summary(self, now: float, hours: float = 12.0) -> dict:
        """A coordinator's end-of-shift handover: what happened in the last
        `hours` of sim time, in numbers a non-technical NGO head can read.
        Everything is scoped to cases CREATED in the window."""
        q = self.store.query
        since = now - hours * 3600
        cases = q("SELECT * FROM cases WHERE created_at >= ?", (since,))
        case_ids = {c["id"] for c in cases}
        outs = [o for o in q("SELECT * FROM outcomes WHERE created_at >= ?", (since,))
                if o["case_id"] in case_ids]
        served = sum(1 for o in outs if o["served"])
        escalated = sum(1 for o in outs if o["escalated"])
        not_found = sum(1 for o in outs if not o["found"])
        by_cat: dict[str, int] = {}
        for c in cases:
            by_cat[c["category"] or "unknown"] = by_cat.get(c["category"] or "unknown", 0) + 1
        # kit movement in the window, from the audit-quality feed
        kits_out = sum(1 for e in self.feed if e["ts"] >= since and e["kind"] == "kit_pickup")
        returns = sum(1 for e in self.feed if e["ts"] >= since and e["kind"] == "kit_return")
        restocks = sum(1 for e in self.feed if e["ts"] >= since and e["kind"] == "restock_delivered")
        accept_times = [r["accepted_at"] - r["created_at"] for r in
                        q("SELECT created_at, accepted_at FROM orders "
                          "WHERE accepted_at IS NOT NULL AND created_at >= ?", (since,))]
        still_open = sum(1 for c in cases if c["status"] not in ("closed", "escalated"))
        return {
            "window_hours": hours,
            "generated_sim": now,
            "reports_received": len(cases),
            "people_served": served,
            "clinical_escalations": escalated,
            "not_found": not_found,
            "still_open_at_handover": still_open,
            "by_category": by_cat,
            "median_accept_s": round(statistics.median(accept_times)) if accept_times else None,
            "kits_delivered": kits_out,
            "kits_returned_unused": returns,
            "courier_restocks": restocks,
            "kits_on_hand": self.metrics()["kits"],
            "low_stock_skus": self.metrics()["kits_low"],
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
        # evict the same idle conversations from memory that the purge forgot
        cutoff = self.now() - self.cfg.conversation_ttl_s
        kept = self.store.query("SELECT phone FROM conversations")
        alive = {r["phone"] for r in kept}
        for phone in [p for p in self.conversations
                      if p not in alive and self._last_activity(p) < cutoff]:
            self.conversations.pop(phone, None)
            self._msg_times.pop(phone, None)
        self.emit("purge", stats)
        return stats

    def _last_activity(self, phone: str) -> float:
        conv = self.conversations.get(phone)
        if not conv or not conv.log:
            return 0.0
        return conv.log[-1].get("ts", 0.0)

    def digipin_for(self, lat: float | None, lng: float | None) -> str | None:
        if lat is None or lng is None:
            return None
        try:
            return digipin.encode(lat, lng)
        except ValueError:
            return None
