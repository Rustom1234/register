"""Emergency-gate golden set. 100% recall on emergencies is a BLOCKING
requirement (build plan §6) — if any of these stops matching, the build
must fail."""

from pukaar import gate

EMERGENCIES = [
    "Ek aadmi behosh pada hai sadak par",
    "aadmi behosh hai flyover ke neeche",
    "He is unconscious near the gate",
    "bahut khoon beh raha hai",
    "khoon ruk nahi raha",
    "bleeding heavily from the head",
    "blood everywhere please help",
    "saans nahi le pa raha",
    "he is not breathing",
    "can't breathe properly",
    "accident ho gaya hai truck se",
    "gaadi ne maar di ek aadmi ko",
    "train se gir gaya track par",
    "he collapsed suddenly",
    "usko daura pad raha hai",
    "seizure ho raha hai",
    "aag lag gayi hai jhuggi mein",
    "current lag gaya hai",
    "ambulance chahiye jaldi",
    "emergency hai please",
    "wo mar raha hai",
]

NON_EMERGENCIES = [
    "Bhaiya flyover ke neeche ek aadmi hai, pair mein patti hai",
    "ek buzurg bhooke hain station ke paas",
    "family baarish mein bheeg rahi hai",
    "usko thand lag rahi hai kambal chahiye",
    "chot lagi hai pair par, chal raha hai",
    "khana chahiye",
    "hello",
]


def test_emergency_recall_100pct():
    misses = [t for t in EMERGENCIES if not gate.is_emergency(t)]
    assert not misses, f"GATE RECALL FAILURE (blocking): {misses}"


def test_non_emergencies_pass_through():
    false_pos = [t for t in NON_EMERGENCIES if gate.is_emergency(t)]
    assert not false_pos, f"unexpected emergency triggers: {false_pos}"


def test_empty_and_none():
    assert not gate.is_emergency(None)
    assert not gate.is_emergency("")
