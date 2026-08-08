"""Intake conversation — a ≤4-step state machine over fixed strings.

The funnel evidence (build plan §3: 56%->12.6% completion over 16 steps in
a comparable WhatsApp program) makes brevity a design law: location ->
category -> one optional extras ask -> done. The model is used only to
*extract* structure from free text (backends.extract); every sentence the
witness sees is a fixed string. The deterministic 112 gate runs first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import gate, strings
from .backends import Backend, BackendError


@dataclass
class BotMsg:
    text: str
    buttons: list[dict] = field(default_factory=list)
    string_id: str = ""


@dataclass
class Conversation:
    phone_hash: str
    state: dict = field(default_factory=lambda: {
        "stage": "new",           # new -> need_location -> need_category -> extras -> done
        "turns": 0,
        "lat": None, "lng": None, "geo_conf": None, "landmark_text": None,
        "category": None, "category_conf": 0.0,
        "freshness_min": None, "detail": None, "photo_hint": None,
        "location_asked": False,
        "stopped": False, "ready_case": None, "case_id": None,
    })
    log: list[dict] = field(default_factory=list)

    def remember(self, sender: str, kind: str, text: str, buttons: list | None = None, ts: float = 0.0) -> None:
        self.log.append({"from": sender, "kind": kind, "text": text, "buttons": buttons or [], "ts": ts})


MAX_TURNS = 8


class Intake:
    def __init__(self, backend: Backend):
        self.backend = backend

    # ------------------------------------------------------------------
    def handle(self, conv: Conversation, kind: str, text: str | None = None,
               lat: float | None = None, lng: float | None = None,
               photo_hint: str | None = None) -> list[BotMsg]:
        s = conv.state
        out: list[BotMsg] = []
        s["turns"] += 1

        # The 112 gate outranks everything — even a stopped conversation.
        # A witness who opted out and then texts an emergency gets the fixed
        # redirect, never silence.
        if kind == "text" and gate.is_emergency(text):
            s["stopped"] = False
            if s["stage"] == "done":
                self._reset_report(s)
            s["stage"] = "emergency_redirect"
            return [BotMsg(strings.SAFETY["S-112"], string_id="S-112")]

        if s["stopped"]:
            # S-STOP promises "you can always write back" — a fresh text
            # re-opens the line; everything else stays silent.
            if kind == "text" and text and text.strip().upper() != "STOP":
                s["stopped"] = False
                if s["stage"] == "done":
                    self._reset_report(s)
                    s["stage"] = "new"
            else:
                return []

        if kind == "text" and text and text.strip().upper() == "STOP":
            s["stopped"] = True
            return [BotMsg(strings.SAFETY["S-STOP"], string_id="S-STOP")]

        # "Still there?" replies work even after the report is filed.
        if kind == "button" and text and text.startswith("still:"):
            s["_recheck_reply"] = text.split(":", 1)[1]
            sid = "S-STILLTHERE-YES" if s["_recheck_reply"] == "yes" else "S-STILLTHERE-NO"
            return [BotMsg(strings.SAFETY[sid], string_id=sid)]

        # After a report is filed: stray button taps are absorbed silently;
        # fresh text/location/photo starts a NEW report on the same number.
        if s["stage"] == "done":
            if kind == "button":
                return []
            self._reset_report(s)
            s["stage"] = "need_location"

        first_contact = s["stage"] == "new"
        if first_contact:
            out.append(BotMsg(strings.SAFETY["S-NOTICE"], string_id="S-NOTICE"))
            s["stage"] = "need_location"

        self._absorb(s, kind, text, lat, lng, photo_hint)

        # Finalize when we have the essentials or the turn budget is spent.
        if self._has_location(s) and s["category"] and (s["stage"] == "extras_done" or s["turns"] >= MAX_TURNS):
            s["ready_case"] = self._case_payload(conv)
            s["stage"] = "done"
            return out  # S-EXPECT is sent by the service once the case id exists

        # Otherwise ask for exactly the next missing thing.
        if not self._has_location(s):
            if s.get("location_asks", 0) >= 2 and (s.get("detail") or s.get("landmark_text")):
                # Terminal human rung (NGO-ops audit): two unanswered pin
                # asks means the witness's words aren't in our landmark
                # vocabulary — adopt what they SAID as a landmark-only
                # location and let the coordinator's request-pin rail take
                # it, instead of asking "where?" forever and filing nothing.
                s["landmark_text"] = s["landmark_text"] or (s["detail"] or "")[:80]
                s["geo_conf"] = "landmark"
                s["location_asked"] = True
            else:
                s["stage"] = "need_location"
                s["location_asked"] = True
                s["location_asks"] = s.get("location_asks", 0) + 1
                out.append(BotMsg(strings.SAFETY["S-ASK-LOCATION"], string_id="S-ASK-LOCATION"))
                return out
        if not s["category"]:
            s["stage"] = "need_category"
            out.append(BotMsg(strings.SAFETY["S-ASK-CATEGORY"],
                              buttons=list(strings.CATEGORY_BUTTONS), string_id="S-ASK-CATEGORY"))
        else:
            if s["stage"] != "extras_asked":
                s["stage"] = "extras_asked"
                out.append(BotMsg(strings.SAFETY["S-ASK-EXTRA"],
                                  buttons=list(strings.FRESHNESS_BUTTONS), string_id="S-ASK-EXTRA"))
            else:
                # Their reply to the extras ask (whatever it was) completes intake.
                s["stage"] = "extras_done"
                s["ready_case"] = self._case_payload(conv)
                s["stage"] = "done"
        return out

    # ------------------------------------------------------------------
    @staticmethod
    def _reset_report(s: dict) -> None:
        """Clear all per-report slots so a new report starts clean —
        including urgency, which must never leak from an earlier report."""
        for slot in ("lat", "lng", "geo_conf", "landmark_text", "category",
                     "freshness_min", "detail", "photo_hint"):
            s[slot] = None
        s.pop("urgency", None)
        s["category_conf"], s["location_asked"], s["turns"] = 0.0, False, 1

    # ------------------------------------------------------------------
    def _absorb(self, s: dict, kind: str, text: str | None,
                lat: float | None, lng: float | None, photo_hint: str | None) -> None:
        if kind == "location" and lat is not None and lng is not None:
            s["lat"], s["lng"], s["geo_conf"] = lat, lng, "pin"
        if kind == "photo":
            s["photo_hint"] = photo_hint or "photo"
            try:
                hint = self.backend.photo_assist(s["photo_hint"])
                if hint["category_hint"] and not s["category"]:
                    s["category"] = hint["category_hint"]
                    s["category_conf"] = min(0.75, hint["confidence"])  # assist-only ceiling
                if hint["urgency_hint"] == "high":
                    s["urgency"] = "high"
            except BackendError:
                pass
            if s["stage"] == "extras_asked":
                s["stage"] = "extras_done"
        if kind == "button" and text:
            if text.startswith("cat:"):
                value = text.split(":", 1)[1]
                if value in ("medical", "food", "shelter"):  # never trust the wire
                    s["category"] = value
                    s["category_conf"] = 1.0
            elif text.startswith("fresh:"):
                try:
                    s["freshness_min"] = int(text.split(":", 1)[1])
                except ValueError:
                    pass  # malformed tap absorbed, like any unknown button
                else:
                    if s["stage"] == "extras_asked":
                        s["stage"] = "extras_done"
        if kind == "text" and text:
            try:
                ex = self.backend.extract(text, has_photo=bool(s["photo_hint"]))
            except BackendError:
                ex = {"category": None, "landmark_text": None, "freshness_min": None,
                      "detail": text[:140], "confidence": 0.0}
            if ex["category"] and ex["confidence"] >= 0.8 and not s["category"]:
                s["category"], s["category_conf"] = ex["category"], ex["confidence"]
            if ex["landmark_text"] and not s["landmark_text"]:
                s["landmark_text"] = ex["landmark_text"]
                if not self._has_location(s):
                    s["geo_conf"] = "landmark"
            if ex["freshness_min"] is not None and s["freshness_min"] is None:
                s["freshness_min"] = ex["freshness_min"]
            if ex["detail"]:
                s["detail"] = (s["detail"] + " | " + ex["detail"])[:280] if s["detail"] else ex["detail"]
            if s["stage"] == "extras_asked":
                s["stage"] = "extras_done"

    @staticmethod
    def _has_location(s: dict) -> bool:
        # A pin always counts. A landmark counts only after we asked for a pin
        # once and the witness answered with text instead — it's the fallback
        # (build plan §3: pin + landmark, Swiggy/Zomato multi-field lesson).
        if s["lat"] is not None:
            return True
        return bool(s["location_asked"] and s["landmark_text"])

    @staticmethod
    def _case_payload(conv: Conversation) -> dict:
        s = conv.state
        return {
            "lat": s["lat"], "lng": s["lng"], "geo_conf": s["geo_conf"] or "landmark",
            "landmark_text": s["landmark_text"],
            "category": s["category"], "category_conf": s["category_conf"],
            "freshness_min": s["freshness_min"], "detail": s["detail"],
            "urgency": s.get("urgency", "medium"),
            "photo_hint": s["photo_hint"], "reporter_hash": conv.phone_hash,
        }
