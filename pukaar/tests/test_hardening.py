"""Risk-register fixes: conversation persistence, rate limiting,
coordinator request-pin, manual arrived, webhook signatures, watchdog."""

import hashlib
import hmac as hmac_mod
import json

from fastapi.testclient import TestClient

from pukaar import geo
from pukaar.api import build_app
from pukaar.config import Config
from pukaar.db import Store
from pukaar.service import PukaarService
from pukaar.whatsapp import verify_signature


class _Clock:
    def __init__(self, t=10 * 3600.0):
        self.t = t

    def __call__(self):
        return self.t


def _svc(store=None, clock=None):
    cfg = Config()
    cfg.backend = "mock"
    return cfg, PukaarService(cfg, store or Store(":memory:"), now_fn=clock or _Clock())


# ---------------------------------------------------------- persistence --

def test_conversation_survives_restart():
    store = Store(":memory:")
    clock = _Clock()
    _, svc1 = _svc(store, clock)
    svc1.wa_inbound("+91-P1", "text", text="An injured man is near the gate")
    svc1.wa_inbound("+91-P1", "location", lat=28.5933, lng=77.2507)

    # "restart": a brand-new service over the same store
    _, svc2 = _svc(store, clock)
    conv = svc2.conversations.get("+91-P1")
    assert conv is not None, "conversation must reload from the store"
    assert conv.state.get("lang") == "en"
    assert conv.state["lat"] == 28.5933
    assert any(m["from"] == "witness" for m in conv.log)

    # ...and the intake continues where it left off (no restart notice, no reset)
    replies = svc2.wa_inbound("+91-P1", "button", text="fresh:10")
    assert any(r.string_id in ("S-EXPECT", "S-EXPECT-NIGHT") for r in replies), \
        "mid-intake witness should complete the SAME report after restart"


def test_idle_conversations_purged():
    store = Store(":memory:")
    clock = _Clock()
    cfg, svc = _svc(store, clock)
    svc.wa_inbound("+91-P2", "text", text="hello there")
    clock.t += cfg.conversation_ttl_s + 60
    svc.run_purge()
    assert store.one("SELECT * FROM conversations WHERE phone='+91-P2'") is None
    assert "+91-P2" not in svc.conversations


# ---------------------------------------------------------- rate limit --

def test_rate_limit_says_slowdown_then_silence_but_112_passes():
    cfg, svc = _svc()
    for i in range(cfg.rate_limit_msgs):
        svc.wa_inbound("+91-R1", "text", text=f"spam message {i}")
    over = svc.wa_inbound("+91-R1", "text", text="one more")
    assert [r.string_id for r in over] == ["S-SLOWDOWN"]
    assert svc.wa_inbound("+91-R1", "text", text="again") == []
    # the gate outranks the limiter
    e = svc.wa_inbound("+91-R1", "text", text="aadmi behosh pada hai!!")
    assert any(r.string_id == "S-112" for r in e)


# ----------------------------------------------------- request-pin flow --

def test_request_pin_updates_case_not_new_report():
    cfg, svc = _svc()
    # landmark-only report (asked once, then landmark text accepted)
    svc.wa_inbound("+91-Q1", "text", text="aadmi ghayal hai kahin")
    svc.wa_inbound("+91-Q1", "text", text="flyover ke neeche gate 3 ke paas")
    svc.wa_inbound("+91-Q1", "button", text="fresh:10")
    case = svc.store.one("SELECT * FROM cases")
    assert case is not None and case["lat"] is None

    assert svc.request_pin(case["id"]) is True
    conv = svc.conversations["+91-Q1"]
    assert conv.state["await_pin_case"] == case["id"]

    replies = svc.wa_inbound("+91-Q1", "location", lat=28.594, lng=77.252)
    assert [r.string_id for r in replies] == ["S-PIN-THANKS"]
    case = svc.store.one("SELECT * FROM cases WHERE id=?", (case["id"],))
    assert case["lat"] == 28.594 and case["cell"] == geo.cell_key(28.594, 77.252)
    assert len(svc.store.query("SELECT * FROM cases")) == 1, "no duplicate case"


def test_request_pin_refuses_pinned_case():
    cfg, svc = _svc()
    svc.wa_inbound("+91-Q2", "text", text="aadmi ghayal hai")
    svc.wa_inbound("+91-Q2", "location", lat=28.5933, lng=77.2507)
    svc.wa_inbound("+91-Q2", "button", text="fresh:10")
    case = svc.store.one("SELECT * FROM cases")
    assert svc.request_pin(case["id"]) is False


# ------------------------------------------------- arrived + watchdog --

def test_manual_arrived_over_http():
    cfg = Config()
    cfg.backend = "mock"
    with TestClient(build_app(cfg)) as client:
        svc = client.app.state.svc
        svc.store.insert("responders", {"id": "r1", "partner_id": "partner_1",
                                        "display_name": "R", "medical": 0,
                                        "vetting": "verified", "active": 1})
        svc.positions["r1"] = (28.5933, 77.2507)
        for m in ({"phone": "+91-A9", "kind": "text", "text": "aadmi ghayal hai"},
                  {"phone": "+91-A9", "kind": "location", "lat": 28.5933, "lng": 77.2507},
                  {"phone": "+91-A9", "kind": "button", "text": "fresh:10"}):
            client.post("/api/wa/inbound", json=m)
        svc.dispatch.tick()
        a = svc.store.one("SELECT * FROM assignments WHERE responded_at IS NULL")
        svc.dispatch.respond(a["id"], True)
        order = svc.store.one("SELECT * FROM orders")
        r = client.post("/api/responder", json={"action": "arrived", "order_id": order["id"]})
        assert r.json()["ok"]
        assert svc.store.one("SELECT * FROM orders")["status"] == "onsite"

        h = client.get("/health").json()
        assert "tick_age_s" in h and h["tick_age_s"] >= 0


# -------------------------------------------------- webhook signatures --

def test_webhook_signature_verification():
    secret = "shhh"
    body = json.dumps({"entry": []}).encode()
    good = "sha256=" + hmac_mod.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_signature(body, good, secret)
    assert not verify_signature(body, "sha256=" + "0" * 64, secret)
    assert not verify_signature(body, None, secret)
    assert verify_signature(body, None, "")     # unset secret -> check disabled


def test_webhook_rejects_bad_signature_when_secret_set(monkeypatch):
    monkeypatch.setenv("WA_APP_SECRET", "topsecret")
    cfg = Config()
    cfg.backend = "mock"
    with TestClient(build_app(cfg)) as client:
        r = client.post("/webhook", json={"entry": []})
        assert r.status_code == 403
