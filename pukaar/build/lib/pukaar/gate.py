"""Deterministic emergency gate — runs BEFORE any model call.

This is both the safety measure and the liability shield (build plan §5):
no generated text ever sits in the emergency path. Patterns are
deliberately high-recall; a false positive costs one fixed 112 message,
a false negative could cost a life. The golden test (tests/test_gate.py)
requires 100% recall on the emergency set and blocks CI on regression.
"""

from __future__ import annotations

import re

_PATTERNS = [
    # unconscious
    r"\bbehosh\b", r"\bbeh?osh\b", r"unconscious", r"not\s+waking", r"hosh\s+nahi",
    # heavy bleeding
    r"bahut\s+khoon", r"khoon\s+beh", r"khoon\s+hi\s+khoon", r"bleeding\s+(a\s+lot|heavily|badly)",
    r"blood\s+everywhere", r"khoon\s+ruk\s+nahi",
    # breathing
    r"saans\s+nahi", r"not\s+breathing", r"can'?t\s+breathe", r"breathing\s+problem",
    # accident / vehicle / train
    r"\baccident\b", r"\btakkar\b", r"gaadi\s+ne\s+maar", r"train\s+se", r"track\s+par\s+gir",
    # collapse / seizure
    r"\bcollapsed?\b", r"\bgir\s+ke\s+behosh", r"\bdaura\b", r"\bseizure\b", r"\bfits?\s+aa",
    # fire / electrocution
    r"\baag\s+lag", r"\bon\s+fire\b", r"current\s+lag", r"\belectrocut",
    # explicit sos
    r"\bemergency\b", r"\bambulance\b", r"\bmar\s+raha\b", r"\bmar\s+rahi\b", r"\bdying\b",
    # Devanagari mirrors — deva is a fully supported witness language, so the
    # gate must catch it too (\b doesn't work across Devanagari; match bare).
    r"बेहोश",                              # unconscious
    r"होश\s*(में\s*)?नहीं",                 # not conscious
    r"बहुत\s*खून", r"खून\s*बह", r"खून\s*रुक\s*नहीं",   # heavy bleeding
    r"साँ?स\s*नहीं", r"सांस\s*नहीं",         # not breathing
    r"एक्सिडेंट", r"एक्सीडेंट", r"टक्कर", r"गाड़ी\s*ने\s*मार",  # accident
    r"दौरा", r"गिर\s*के\s*बेहोश",            # seizure / collapse
    r"आग\s*लग", r"करंट\s*लग", r"बिजली\s*का\s*झटका",   # fire / electrocution
    r"एम्बुलेंस", r"एंबुलेंस", r"मर\s*रह[ाी]", r"इमरजेंसी",  # explicit sos
]

_RX = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


def is_emergency(text: str | None) -> bool:
    if not text:
        return False
    return any(rx.search(text) for rx in _RX)
