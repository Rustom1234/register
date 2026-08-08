"""Emergency-gate golden set. 100% recall on emergencies is a BLOCKING
requirement (build plan §6) — if any of these stops matching, the build
must fail."""

from pukaar import gate

EMERGENCIES = [
    "Ek aadmi behosh pada hai sadak par",
    "aadmi behosh hai flyover ke neeche",
    "He is unconscious near the gate",
    "bahut khoon beh raha hai",
    "zyada khoon beh gaya hai",
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
    # CTO-audit additions: the common ways witnesses describe a dying person
    # that the first pattern set missed
    "he is having a heart attack",
    "seene mein dard ho raha hai",
    "chest pain ho raha hai bahut",
    "someone is having a stroke",
    "lakwa maar gaya hai",
    "a man is drowning in the canal",
    "baccha paani mein doob raha hai",
    "he cannot breathe at all",
    "uska dam ghut raha hai",
    "he is choking on something",
    "she is in labour, baby coming now",
    "labour pain ho raha hai",
    "baccha aa raha hai abhi",
    "wo suicide karne ja raha hai",
    "khudkushi kar raha hai chhat se",
    # Devanagari — a supported witness language must never bypass the gate
    "एक आदमी बेहोश पड़ा है सड़क पर",
    "बहुत खून बह रहा है",
    "खून रुक नहीं रहा",
    "सांस नहीं ले पा रहा",
    "एक्सीडेंट हो गया है ट्रक से",
    "गाड़ी ने मार दी",
    "उसको दौरा पड़ रहा है",
    "आग लग गयी है झुग्गी में",
    "करंट लग गया है",
    "एम्बुलेंस चाहिए जल्दी",
    "वो मर रहा है",
    "इमरजेंसी है",
]

NON_EMERGENCIES = [
    "Bhaiya flyover ke neeche ek aadmi hai, pair mein patti hai",
    "ek buzurg bhooke hain station ke paas",
    "family baarish mein bheeg rahi hai",
    "usko thand lag rahi hai kambal chahiye",
    "chot lagi hai pair par, chal raha hai",
    "khana chahiye",
    "hello",
    # place names and everyday phrases that MUST NOT trip the new patterns
    "labour chowk ke paas ek aadmi hai",
    # ordinary wound reports in everyday Hindi are KIT RUNS, not 112 bounces
    # (NGO-ops audit: bouncing these refuses service in the catchment
    # language while identical English goes to intake)
    "pair se khoon beh raha hai",
    "uske haath se khoon aa raha hai",
    "पैर से खून बह रहा है",
    "daily labour karta hai wo",
    "kit delivery ho gayi thi kal",
    "the food delivery guy saw him near the park",
    # Devanagari non-emergencies stay ordinary reports
    "फ्लाईओवर के नीचे एक आदमी है, पैर में पट्टी है",
    "एक बुज़ुर्ग भूखे हैं स्टेशन के पास",
    "खाना चाहिए",
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
