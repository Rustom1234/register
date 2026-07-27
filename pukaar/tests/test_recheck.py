"""The "still there?" witness re-ping: stale unserved cases ask their
witness once; yes refreshes, no closes honestly (found=0)."""

from pukaar import geo


def _file_report(svc, phone, lat=28.5933, lng=77.2507, text="aadmi ghayal hai"):
    svc.wa_inbound(phone, "text", text=text)
    svc.wa_inbound(phone, "location", lat=lat, lng=lng)
    svc.wa_inbound(phone, "button", text="fresh:10")


def _bot_msgs(svc, phone):
    return [m for m in svc.conversations[phone].log if m["from"] == "bot"]


def test_recheck_sent_once_after_threshold(svc, clock, cfg):
    _file_report(svc, "+91-R1")           # no responders -> stays unserved
    svc.dispatch.tick()
    clock.advance(cfg.recheck_after_s + 60)
    svc.tick_recheck()
    msgs = _bot_msgs(svc, "+91-R1")
    ask = [m for m in msgs if "wahin hai?" in m["text"]]
    assert len(ask) == 1
    assert any(b["id"] == "still:yes" for b in ask[0]["buttons"])

    svc.tick_recheck()                    # ask-once: no duplicate
    msgs2 = [m for m in _bot_msgs(svc, "+91-R1") if "wahin hai?" in m["text"]]
    assert len(msgs2) == 1


def test_recheck_yes_refreshes(svc, clock, cfg):
    _file_report(svc, "+91-R2")
    svc.dispatch.tick()
    clock.advance(cfg.recheck_after_s + 60)
    svc.tick_recheck()
    replies = svc.wa_inbound("+91-R2", "button", text="still:yes")
    assert any(r.string_id == "S-STILLTHERE-YES" for r in replies)
    case = svc.store.one("SELECT * FROM cases")
    assert case["freshness_min"] == 0
    assert case["status"] != "closed"
    assert any(e["kind"] == "recheck_confirmed" for e in svc.feed)


def test_recheck_no_closes_honestly(svc, clock, cfg):
    _file_report(svc, "+91-R3")
    svc.dispatch.tick()
    clock.advance(cfg.recheck_after_s + 60)
    svc.tick_recheck()
    replies = svc.wa_inbound("+91-R3", "button", text="still:no")
    assert any(r.string_id == "S-STILLTHERE-NO" for r in replies)
    case = svc.store.one("SELECT * FROM cases")
    assert case["status"] == "closed"
    out = svc.store.one("SELECT * FROM outcomes")
    assert out["found"] == 0 and out["served"] == 0 and out["closed_by"] == "witness"
    order = svc.store.one("SELECT * FROM orders")
    assert order["status"] == "closed"


def test_recheck_not_sent_for_served_cases(svc, clock, cfg):
    base = (28.5933, 77.2507)
    svc.store.insert("responders", {"id": "resp_1", "partner_id": "partner_1",
                                    "display_name": "Meena", "medical": 0,
                                    "vetting": "verified", "active": 1})
    svc.positions["resp_1"] = geo.offset_m(*base, 100, 0)
    _file_report(svc, "+91-R4", *base)
    svc.dispatch.tick()
    a = svc.store.one("SELECT * FROM assignments WHERE responded_at IS NULL")
    svc.dispatch.respond(a["id"], True)
    order = svc.store.one("SELECT * FROM orders")
    svc.dispatch.arrived(order["id"])
    svc.dispatch.close(order["id"], "served")
    clock.advance(cfg.recheck_after_s + 60)
    svc.tick_recheck()
    assert not any("wahin hai?" in m["text"] for m in _bot_msgs(svc, "+91-R4"))


def test_recheck_english_witness(svc, clock, cfg):
    _file_report(svc, "+91-R5", text="An injured man is lying here with a bandage")
    svc.dispatch.tick()
    clock.advance(cfg.recheck_after_s + 60)
    svc.tick_recheck()
    msgs = _bot_msgs(svc, "+91-R5")
    ask = [m for m in msgs if "still there?" in m["text"]]
    assert ask and any(b["label"] == "Yes, still there" for b in ask[0]["buttons"])


def test_health_endpoint():
    from fastapi.testclient import TestClient

    from pukaar.api import build_app
    from pukaar.config import Config

    cfg = Config()
    cfg.backend = "mock"
    with TestClient(build_app(cfg)) as client:
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True and body["backend"] == "mock"
