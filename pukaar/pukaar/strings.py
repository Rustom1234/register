"""Fixed strings — every safety-critical or policy-bearing message lives here.

Design rule (build plan §5, Air Canada precedent): the bot never *generates*
emergency guidance, medical wording, promises, or notices. Models structure
information; humans and fixed strings speak. IDs are stable so audits can
reference exactly what was sent.

Hindi is transliterated (Hinglish) for the demo; a native-script pass is a
launch task, not a code change.
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
    "S-CLOSURE-SERVED": "🟢 Aapki report {case_id}: karyakarta vyakti tak pahuncha aur madad de di gayi. Shukriya!",
    "S-CLOSURE-ESCALATED": "🟢 Aapki report {case_id}: madad de di gayi, aur medical team ko bhi bulaya gaya hai. Shukriya!",
    "S-CLOSURE-NOTFOUND": "🟡 Aapki report {case_id}: karyakarta pahuncha par vyakti nahi mila. Report record mein hai.",
    "S-CLOSURE-DECLINED": "🟡 Aapki report {case_id}: vyakti ne madad lene se mana kiya. Unki marzi ka samman kiya gaya.",
    "S-STOP": "Theek hai — aapka number hata diya gaya hai. Kabhi bhi wapas likh sakte hain.",
    "S-NIGHT": (
        "Raat ke samay dispatch band hai. Emergency: 112. Shelter rescue (Delhi): "
        "14461 / DUSIB WhatsApp 9871013284. Aapki report subah ki round mein sabse pehle jayegi."
    ),
    "S-UNKNOWN": "Samajh nahi paya. Location pin 📍, photo, ya chhota sa message bhejein.",
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


def fmt(string_id: str, **kw: object) -> str:
    return SAFETY[string_id].format(**kw)
