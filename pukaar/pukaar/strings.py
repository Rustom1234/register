"""Fixed strings — every safety-critical or policy-bearing message lives here.

Design rule (build plan §5, Air Canada precedent): the bot never *generates*
emergency guidance, medical wording, promises, or notices. Models structure
information; humans and fixed strings speak. IDs are stable so audits can
reference exactly what was sent.

Three parallel tables share one canonical set of IDs: SAFETY (Hinglish),
SAFETY_DEVA (Devanagari), SAFETY_EN (English). The service picks per
conversation (auto language mirroring) or per the global override.
"""

from __future__ import annotations

SAFETY = {
    # Emergency exit — sent by the deterministic gate BEFORE any model call.
    "S-112": (
        "⚠️ Yeh emergency lagti hai. Abhi 112 par call karein. "
        "Raat mein shelter/rescue ke liye: 14461 (DUSIB, Delhi). "
        "Pukaar emergency service nahi hai."
    ),
    # First-contact notice (DPDP Rule 3 style, compact)
    "S-NOTICE": (
        "Namaste 🙏 Yeh Pukaar hai — aap kisi zarooratmand vyakti ki soochna de "
        "sakte hain. Hum sirf aapka number (hash), pin aur bheji gayi jaankari "
        "rakhte hain; photo case band hone par delete ho jaati hai. "
        "Rukna ho to STOP likhein."
    ),
    "S-ASK-LOCATION": "Vyakti kahan hai? 📍 Location pin bhejein (ya landmark likhein).",
    "S-ASK-CATEGORY": "Kya zaroorat dikh rahi hai? Ek chunein:",
    "S-ASK-EXTRA": (
        "Shukriya. Ho sake to aas-paas ki photo bhejein (chehra zaroori nahi) "
        "aur batayein — kitni der pehle dekha?"
    ),
    "S-EXPECT": (
        "✅ Report darj ho gayi (ID {case_id}). Ek bharosemand karyakarta aaj "
        "hi pahunchne ki koshish karega. Dhanyavaad rukne ke liye."
    ),
    # Night version makes no same-day promise — honesty over comfort
    # (build plan §3.12: never promise a response we can't staff).
    "S-EXPECT-NIGHT": (
        "✅ Report darj ho gayi (ID {case_id}). Raat mein dispatch band hai — "
        "aapki report subah ki pehli round mein jayegi. Turant zaroorat ho to: "
        "112 (emergency) ya 14461 (DUSIB shelter rescue, Delhi). Dhanyavaad."
    ),
    "S-STILLTHERE": "🤔 Aapki report {case_id} tak abhi koi pahunch nahi paya. Kya vyakti abhi bhi wahin hai?",
    "S-STILLTHERE-YES": "Shukriya! Team ko bata diya — report taaza kar di gayi hai.",
    "S-STILLTHERE-NO": "Theek hai — report band kar di gayi hai. Rukne ke liye dhanyavaad.",
    "S-PROGRESS-ACCEPTED": "🛵 Ek karyakarta ({name}) aapki report {case_id} ke liye nikal chuka hai.",
    "S-PROGRESS-ARRIVED": "📍 Karyakarta vyakti ke paas pahunch gaya hai (report {case_id}).",
    "S-CLOSURE-SERVED": "🟢 Aapki report {case_id}: karyakarta vyakti tak pahuncha aur madad de di gayi. Shukriya!",
    "S-CLOSURE-ESCALATED": "🟢 Aapki report {case_id}: madad de di gayi, aur medical team ko bhi bulaya gaya hai. Shukriya!",
    "S-CLOSURE-NOTFOUND": "🟡 Aapki report {case_id}: karyakarta pahuncha par vyakti nahi mila. Report record mein hai.",
    "S-CLOSURE-DECLINED": "🟡 Aapki report {case_id}: vyakti ne madad lene se mana kiya. Unki marzi ka samman kiya gaya.",
    "S-STOP": "Theek hai — aapka number hata diya gaya hai. Kabhi bhi wapas likh sakte hain.",
}

CATEGORY_LABELS = {
    "medical": "🩹 Chot / Injury",
    "food": "🍚 Bhookh / Hunger",
    "shelter": "🌧️ Thand-Baarish / Shelter",
}

CATEGORY_BUTTONS = [
    {"id": "cat:medical", "label": CATEGORY_LABELS["medical"]},
    {"id": "cat:food", "label": CATEGORY_LABELS["food"]},
    {"id": "cat:shelter", "label": CATEGORY_LABELS["shelter"]},
]

STILL_BUTTONS = [
    {"id": "still:yes", "label": "Haan, wahin hai"},
    {"id": "still:no", "label": "Nahi / pata nahi"},
]

FRESHNESS_BUTTONS = [
    {"id": "fresh:10", "label": "Abhi / just now"},
    {"id": "fresh:60", "label": "~1 ghanta pehle"},
    {"id": "fresh:240", "label": "Kaafi der pehle"},
]

# Responder-card instruction strings, referenced by ID from orders.
INSTRUCTIONS = {
    "MI-1": "Gloves pehnein. Purani patti na hataayein — upar se saaf dressing.",
    "MI-2": "Ghaav laal/sooja ho ya bukhar lage to clinical team ko turant flag karein.",
    "MI-3": "Paani pehle offer karein, phir baat shuru karein.",
    "FI-1": "Khana dene se pehle poochein — kitne log hain?",
    "FI-2": "Garmi ho to ORS + paani zaroor saath dein.",
    "SI-1": "Shelter jaana chahein to coordinator ko batayein (DUSIB 14461 handoff).",
    "SI-2": "Baarish mein tarpal pehle, baaki baad mein.",
    "GI-1": "Pehle namaste, phir poochh kar hi madad dein. Mana karna unka haq hai.",
}

KIT_SKUS = {
    "MED-1": {"name": "Medical kit", "contents": "antiseptic, gauze, crepe bandage, dressings, gloves, ORS, soap, socks"},
    "FOOD-1": {"name": "Food pack", "contents": "meal, water, ORS, glucose"},
    "SEAS-M": {"name": "Monsoon kit", "contents": "raincoat, tarpaulin sheet, socks, soap"},
    "SEAS-W": {"name": "Winter kit", "contents": "blanket, cap, socks, soap"},
}


# Devanagari mirrors of every witness-facing string. The toggle changes the
# script of what we SEND; incoming Hinglish is understood either way. IDs are
# identical so audits reference one canonical table.
SAFETY_DEVA = {
    "S-112": (
        "⚠️ यह इमरजेंसी लगती है। अभी 112 पर कॉल करें। रात में शेल्टर/रेस्क्यू के लिए: "
        "14461 (DUSIB, दिल्ली)। पुकार इमरजेंसी सेवा नहीं है।"
    ),
    "S-NOTICE": (
        "नमस्ते 🙏 यह पुकार है — आप किसी ज़रूरतमंद व्यक्ति की सूचना दे सकते हैं। "
        "हम सिर्फ़ आपका नंबर (hash), पिन और भेजी गई जानकारी रखते हैं; फोटो केस बंद "
        "होने पर delete हो जाती है। रुकना हो तो STOP लिखें।"
    ),
    "S-ASK-LOCATION": "व्यक्ति कहाँ है? 📍 लोकेशन पिन भेजें (या कोई landmark लिखें)।",
    "S-ASK-CATEGORY": "क्या ज़रूरत दिख रही है? एक चुनें:",
    "S-ASK-EXTRA": (
        "शुक्रिया। हो सके तो आस-पास की फोटो भेजें (चेहरा ज़रूरी नहीं) और बताएं — "
        "कितनी देर पहले देखा?"
    ),
    "S-EXPECT": (
        "✅ रिपोर्ट दर्ज हो गई (ID {case_id})। एक भरोसेमंद कार्यकर्ता आज ही पहुँचने "
        "की कोशिश करेगा। धन्यवाद रुकने के लिए।"
    ),
    "S-EXPECT-NIGHT": (
        "✅ रिपोर्ट दर्ज हो गई (ID {case_id})। रात में डिस्पैच बंद है — आपकी रिपोर्ट "
        "सुबह की पहली राउंड में जाएगी। तुरंत ज़रूरत हो तो: 112 (इमरजेंसी) या 14461 "
        "(DUSIB शेल्टर रेस्क्यू, दिल्ली)। धन्यवाद।"
    ),
    "S-STILLTHERE": "🤔 आपकी रिपोर्ट {case_id} तक अभी कोई पहुँच नहीं पाया। क्या व्यक्ति अभी भी वहीं है?",
    "S-STILLTHERE-YES": "शुक्रिया! टीम को बता दिया — रिपोर्ट ताज़ा कर दी गई है।",
    "S-STILLTHERE-NO": "ठीक है — रिपोर्ट बंद कर दी गई है। रुकने के लिए धन्यवाद।",
    "S-PROGRESS-ACCEPTED": "🛵 एक कार्यकर्ता ({name}) आपकी रिपोर्ट {case_id} के लिए निकल चुका है।",
    "S-PROGRESS-ARRIVED": "📍 कार्यकर्ता व्यक्ति के पास पहुँच गया है (रिपोर्ट {case_id})।",
    "S-CLOSURE-SERVED": "🟢 आपकी रिपोर्ट {case_id}: कार्यकर्ता व्यक्ति तक पहुँचा और मदद दे दी गई। शुक्रिया!",
    "S-CLOSURE-ESCALATED": "🟢 आपकी रिपोर्ट {case_id}: मदद दे दी गई, और मेडिकल टीम को भी बुलाया गया है। शुक्रिया!",
    "S-CLOSURE-NOTFOUND": "🟡 आपकी रिपोर्ट {case_id}: कार्यकर्ता पहुँचा पर व्यक्ति नहीं मिला। रिपोर्ट रिकॉर्ड में है।",
    "S-CLOSURE-DECLINED": "🟡 आपकी रिपोर्ट {case_id}: व्यक्ति ने मदद लेने से मना किया। उनकी मर्ज़ी का सम्मान किया गया।",
    "S-STOP": "ठीक है — आपका नंबर हटा दिया गया है। कभी भी वापस लिख सकते हैं।",
}

CATEGORY_BUTTONS_DEVA = [
    {"id": "cat:medical", "label": "🩹 चोट"},
    {"id": "cat:food", "label": "🍚 भूख"},
    {"id": "cat:shelter", "label": "🌧️ ठंड-बारिश"},
]

STILL_BUTTONS_DEVA = [
    {"id": "still:yes", "label": "हाँ, वहीं है"},
    {"id": "still:no", "label": "नहीं / पता नहीं"},
]

FRESHNESS_BUTTONS_DEVA = [
    {"id": "fresh:10", "label": "अभी देखा"},
    {"id": "fresh:60", "label": "~1 घंटा पहले"},
    {"id": "fresh:240", "label": "काफ़ी देर पहले"},
]


# Plain-English mirrors — the bot answers English witnesses in English.
SAFETY_EN = {
    "S-112": (
        "⚠️ This looks like an emergency. Please call 112 right now. "
        "For night shelter/rescue in Delhi: 14461 (DUSIB). "
        "Pukaar is not an emergency service."
    ),
    "S-NOTICE": (
        "Hello 🙏 This is Pukaar — you can report a person on the street who "
        "needs help. We keep only your number (hashed), the pin, and what you "
        "send; photos are deleted when the case closes. Reply STOP anytime."
    ),
    "S-ASK-LOCATION": "Where is the person? 📍 Share a location pin (or type a nearby landmark).",
    "S-ASK-CATEGORY": "What does the person seem to need? Pick one:",
    "S-ASK-EXTRA": (
        "Thank you. If possible, send a photo of the surroundings (no face "
        "needed) and tell us — how long ago did you see them?"
    ),
    "S-EXPECT": (
        "✅ Your report is registered (ID {case_id}). A trusted outreach "
        "worker will try to reach them today. Thank you for stopping."
    ),
    "S-EXPECT-NIGHT": (
        "✅ Your report is registered (ID {case_id}). Dispatch is closed for "
        "the night — your report goes out with the first morning round. "
        "Urgent right now? 112 (emergency) or 14461 (DUSIB shelter rescue, Delhi)."
    ),
    "S-STILLTHERE": "🤔 No one has been able to reach your report {case_id} yet. Is the person still there?",
    "S-STILLTHERE-YES": "Thank you! The team has been told — your report is refreshed.",
    "S-STILLTHERE-NO": "Okay — the report has been closed. Thank you for stopping.",
    "S-PROGRESS-ACCEPTED": "🛵 An outreach worker ({name}) is on the way for your report {case_id}.",
    "S-PROGRESS-ARRIVED": "📍 The worker has reached the person (report {case_id}).",
    "S-CLOSURE-SERVED": "🟢 Your report {case_id}: an outreach worker reached the person and help was given. Thank you!",
    "S-CLOSURE-ESCALATED": "🟢 Your report {case_id}: help was given, and a medical team has been called in too. Thank you!",
    "S-CLOSURE-NOTFOUND": "🟡 Your report {case_id}: the worker went but couldn't find the person. Your report stays on record.",
    "S-CLOSURE-DECLINED": "🟡 Your report {case_id}: the person chose not to take help. Their choice was respected.",
    "S-STOP": "Okay — your number has been removed. You're welcome back anytime.",
}

CATEGORY_BUTTONS_EN = [
    {"id": "cat:medical", "label": "🩹 Injury"},
    {"id": "cat:food", "label": "🍚 Hunger"},
    {"id": "cat:shelter", "label": "🌧️ Rain-Cold / Shelter"},
]

STILL_BUTTONS_EN = [
    {"id": "still:yes", "label": "Yes, still there"},
    {"id": "still:no", "label": "No / not sure"},
]

FRESHNESS_BUTTONS_EN = [
    {"id": "fresh:10", "label": "Just now"},
    {"id": "fresh:60", "label": "~1 hour ago"},
    {"id": "fresh:240", "label": "A while ago"},
]

_TABLES = {"en": SAFETY_EN, "deva": SAFETY_DEVA}
_CAT_BTNS = {"en": CATEGORY_BUTTONS_EN, "deva": CATEGORY_BUTTONS_DEVA}
_FRESH_BTNS = {"en": FRESHNESS_BUTTONS_EN, "deva": FRESHNESS_BUTTONS_DEVA}
_STILL_BTNS = {"en": STILL_BUTTONS_EN, "deva": STILL_BUTTONS_DEVA}


def _norm(lang: str) -> str:
    return "hinglish" if lang in ("latin", "hinglish") else lang


def text(string_id: str, lang: str = "hinglish") -> str:
    table = _TABLES.get(_norm(lang), {})
    return table.get(string_id, SAFETY[string_id])


def fmt(string_id: str, lang: str = "hinglish", **kw: object) -> str:
    return text(string_id, lang).format(**kw)


def button_label(btn_id: str, lang: str = "hinglish") -> str | None:
    """Reverse lookup: human label for a known quick-reply button ID,
    in the witness's language. None for unknown IDs (free text stays as-is)."""
    lang = _norm(lang)
    for base, per_lang in ((CATEGORY_BUTTONS, _CAT_BTNS), (FRESHNESS_BUTTONS, _FRESH_BTNS),
                           (STILL_BUTTONS, _STILL_BTNS)):
        btns = base if lang == "hinglish" else per_lang.get(lang, base)
        for b in btns:
            if b["id"] == btn_id:
                return b["label"]
    return None


def localized_buttons(buttons: list[dict], lang: str) -> list[dict]:
    lang = _norm(lang)
    if lang == "hinglish" or not buttons:
        return buttons
    if buttons[0]["id"].startswith("cat:"):
        return list(_CAT_BTNS.get(lang, CATEGORY_BUTTONS))
    if buttons[0]["id"].startswith("fresh:"):
        return list(_FRESH_BTNS.get(lang, FRESHNESS_BUTTONS))
    if buttons[0]["id"].startswith("still:"):
        return list(_STILL_BTNS.get(lang, STILL_BUTTONS))
    return buttons
