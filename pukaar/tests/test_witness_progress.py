"""Witness progress updates: accepted -> en-route message, arrival -> reached
message, in the witness's own language. Closure-only feedback loses
witnesses; live progress keeps them."""

from pukaar import geo


def _seed_responder(svc, lat, lng, name="Meena"):
    svc.store.insert("responders", {"id": "resp_1", "partner_id": "partner_1",
                                    "display_name": name, "medical": 1,
                                    "vetting": "verified", "active": 1})
    svc.positions["resp_1"] = (lat, lng)


def _file_report(svc, phone, text, lat=28.5933, lng=77.2507):
    svc.wa_inbound(phone, "text", text=text)
    svc.wa_inbound(phone, "location", lat=lat, lng=lng)
    svc.wa_inbound(phone, "button", text="fresh:10")


def _bot_texts(svc, phone):
    return [m["text"] for m in svc.conversations[phone].log if m["from"] == "bot"]


def test_progress_messages_reach_witness(svc, clock):
    base = (28.5933, 77.2507)
    _seed_responder(svc, *geo.offset_m(*base, 150, 0))
    _file_report(svc, "+91-P1", "aadmi ghayal hai patti se khoon", *base)

    svc.dispatch.tick()
    a = svc.store.one("SELECT * FROM assignments WHERE responded_at IS NULL")
    svc.dispatch.respond(a["id"], True)
    texts = _bot_texts(svc, "+91-P1")
    assert any("nikal chuka hai" in t and "Meena" in t for t in texts), texts

    order = svc.store.one("SELECT * FROM orders")
    svc.dispatch.arrived(order["id"])
    texts = _bot_texts(svc, "+91-P1")
    assert any("pahunch gaya hai" in t for t in texts)

    svc.dispatch.close(order["id"], "served")
    svc.notify_outcome(order["case_id"], "served")
    texts = _bot_texts(svc, "+91-P1")
    assert any("madad de di gayi" in t for t in texts)


def test_progress_in_english_for_english_witness(svc, clock):
    base = (28.5933, 77.2507)
    _seed_responder(svc, *geo.offset_m(*base, 150, 0))
    _file_report(svc, "+91-P2", "An injured man is lying here with a dirty bandage", *base)

    svc.dispatch.tick()
    a = svc.store.one("SELECT * FROM assignments WHERE responded_at IS NULL")
    svc.dispatch.respond(a["id"], True)
    texts = _bot_texts(svc, "+91-P2")
    assert any("is on the way" in t for t in texts), texts


def test_progress_on_manual_assign_too(svc, clock):
    base = (28.5933, 77.2507)
    _file_report(svc, "+91-P3", "aadmi ghayal hai", *base)
    svc.dispatch.tick()          # no responders -> needs_coordinator
    _seed_responder(svc, *geo.offset_m(*base, 200, 0), name="Fatima")
    order = svc.store.one("SELECT * FROM orders")
    assert svc.dispatch.manual_assign(order["id"], "resp_1")
    texts = _bot_texts(svc, "+91-P3")
    assert any("Fatima" in t and "nikal chuka" in t for t in texts)


def test_stopped_witness_gets_no_progress(svc, clock):
    base = (28.5933, 77.2507)
    _seed_responder(svc, *geo.offset_m(*base, 150, 0))
    _file_report(svc, "+91-P4", "aadmi ghayal hai", *base)
    svc.wa_inbound("+91-P4", "text", text="STOP")
    # STOP now deletes the thread outright — the strongest form of
    # "no further messages": there is nothing left to write into.
    assert "+91-P4" not in svc.conversations
    svc.dispatch.tick()
    a = svc.store.one("SELECT * FROM assignments WHERE responded_at IS NULL")
    svc.dispatch.respond(a["id"], True)
    assert "+91-P4" not in svc.conversations