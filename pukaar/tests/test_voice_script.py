"""Voice-note transcripts and the Devanagari script toggle."""


def test_voice_note_flows_like_text(svc):
    phone = "+91-V1"
    svc.wa_inbound(phone, "voice", text="flyover ke neeche aadmi ke pair se khoon aa raha hai")
    svc.wa_inbound(phone, "location", lat=28.5933, lng=77.2507)
    replies = svc.wa_inbound(phone, "button", text="fresh:10")
    assert any(r.string_id == "S-EXPECT" for r in replies)
    case = svc.store.one("SELECT * FROM cases")
    assert case["category"] == "medical"
    conv = svc.conversations[phone]
    first = conv.log[0]
    assert first["kind"] == "voice" and first["text"].startswith("🎤 ")


def test_voice_emergency_still_gated(svc):
    replies = svc.wa_inbound("+91-V2", "voice", text="aadmi behosh pada hai")
    assert [r.string_id for r in replies] == ["S-112"]


def test_deva_script_toggle(svc):
    svc.script = "deva"
    phone = "+91-V3"
    r1 = svc.wa_inbound(phone, "text", text="ek aadmi hai yahan")
    notice = next(r for r in r1 if r.string_id == "S-NOTICE")
    assert "नमस्ते" in notice.text
    r2 = svc.wa_inbound(phone, "location", lat=28.5933, lng=77.2507)
    ask = next(r for r in r2 if r.string_id == "S-ASK-CATEGORY")
    assert "चुनें" in ask.text
    assert any("चोट" in b["label"] for b in ask.buttons)
    svc.wa_inbound(phone, "button", text="cat:food")
    r3 = svc.wa_inbound(phone, "button", text="fresh:10")
    expect = next(r for r in r3 if r.string_id == "S-EXPECT")
    assert "रिपोर्ट दर्ज" in expect.text


def test_latin_default_unchanged(svc):
    r1 = svc.wa_inbound("+91-V4", "text", text="hello")
    notice = next(r for r in r1 if r.string_id == "S-NOTICE")
    assert "Namaste" in notice.text
