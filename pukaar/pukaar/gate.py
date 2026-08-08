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
    r"bahut\s+khoon", r"(?:zyada|tez)\s+khoon", r"khoon\s+hi\s+khoon", r"bleeding\s+(a\s+lot|heavily|badly)",
    r"blood\s+everywhere", r"khoon\s+ruk\s+nahi",
    # breathing — "can(no)t breathe": cannot/can't/cant all count
    r"saans\s+nahi", r"not\s+breathing", r"can(?:'?t|not)\s+breathe", r"breathing\s+problem",
    r"dam\s+ghut", r"\bchok(?:e|ing|ed)\b", r"gala\s+ghut",
    # accident / vehicle / train
    r"\baccident\b", r"\btakkar\b", r"gaadi\s+ne\s+maar", r"train\s+se", r"track\s+par\s+gir",
    # collapse / seizure
    r"\bcollapsed?\b", r"\bgir\s+ke\s+behosh", r"\bdaura\b", r"\bseizure\b", r"\bfits?\s+aa",
    # cardiac / stroke
    r"heart\s+attack", r"seene?\s+m[ea]in?\s+dard", r"chest\s+pain", r"\bstroke\b",
    r"\blakwa\b", r"\bparalys",
    # drowning
    r"\bdrown", r"\bdoob\s+rah", r"paani\s+mein\s+doob",
    # childbirth in progress — birth context required: "Labour Chowk" is a
    # place name in half the cities this could serve
    r"labou?r\s+pain", r"in\s+labou?r\b", r"baby\s+(?:is\s+)?coming",
    r"baccha\s+(?:aa|ho)\s+raha", r"\bdelivery\s+ho\s+rahi", r"jachcha\b",
    # self-harm
    r"\bsuicide\b", r"khudkushi", r"aatm-?hatya", r"jaan\s+de\s+(?:raha|rahi|dega|degi)",
    r"marne\s+(?:ja|wal)[aei]",
    # fire / electrocution
    r"\baag\s+lag", r"\bon\s+fire\b", r"current\s+lag", r"\belectrocut",
    # explicit sos
    r"\bemergency\b", r"\bambulance\b", r"\bmar\s+raha\b", r"\bmar\s+rahi\b", r"\bdying\b",
    # Devanagari mirrors — deva is a fully supported witness language, so the
    # gate must catch it too (\b doesn't work across Devanagari; match bare).
    r"बेहोश",                              # unconscious
    r"होश\s*(में\s*)?नहीं",                 # not conscious
    r"बहुत\s*खून", r"(?:ज़्यादा|तेज़|तेज)\s*खून", r"खून\s*रुक\s*नहीं",   # heavy bleeding
    r"साँ?स\s*नहीं", r"सांस\s*नहीं", r"दम\s*घुट", r"गला\s*घुट",   # not breathing / choking
    r"एक्सिडेंट", r"एक्सीडेंट", r"टक्कर", r"गाड़ी\s*ने\s*मार",  # accident
    r"दौरा", r"गिर\s*के\s*बेहोश",            # seizure / collapse
    r"दिल\s*का\s*दौरा", r"सीने\s*में\s*दर्द", r"लकवा",   # cardiac / stroke
    r"डूब\s*रह", r"पानी\s*में\s*डूब",          # drowning
    r"बच्चा\s*(?:आ|हो)\s*रहा", r"जच्चा",       # childbirth in progress
    r"खुदकुशी", r"आत्म\s*-?\s*हत्या", r"जान\s*दे\s*रह",   # self-harm
    r"आग\s*लग", r"करंट\s*लग", r"बिजली\s*का\s*झटका",   # fire / electrocution
    r"एम्बुलेंस", r"एंबुलेंस", r"मर\s*रह[ाी]", r"इमरजेंसी",  # explicit sos
]

_RX = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


def is_emergency(text: str | None) -> bool:
    if not text:
        return False
    return any(rx.search(text) for rx in _RX)
