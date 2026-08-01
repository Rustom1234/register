"""Phase 2 — rider PWA plumbing, push, SOS, and the overdue safety alarm."""

import json

from fastapi.testclient import TestClient

from pukaar.api import build_app
from pukaar.config import Config


def _client():
    cfg = Config()
    cfg.backend = "mock"
    client = TestClient(build_app(cfg))
    client.__enter__()
    return client, client.app.state.svc, client.app.state.sim


def test_vapid_key_served():
    client, svc, _ = _client()
    r = client.get("/api/push/vapid")
    assert r.status_code == 200
    key = r.json()["key"]
    # pywebpush is installed in this environment, so a key must exist and
    # look like a base64url uncompressed EC point (starts with "B").
    assert key and key.startswith("B")


def test_push_subscribe_stores_and_replaces():
    client, svc, _ = _client()
    sub = {"endpoint": "https://push.example/abc", "keys": {"p256dh": "x", "auth": "y"}}
    r = client.post("/api/push/subscribe", json={"responder_id": "resp_1", "subscription": sub})
    assert r.status_code == 200 and r.json()["ok"]
    rows = svc.store.query("SELECT * FROM push_subs")
    assert len(rows) == 1 and rows[0]["responder_id"] == "resp_1"
    # same endpoint re-subscribed by another responder replaces, not duplicates
    client.post("/api/push/subscribe", json={"responder_id": "resp_2", "subscription": sub})
    rows = svc.store.query("SELECT * FROM push_subs")
    assert len(rows) == 1 and rows[0]["responder_id"] == "resp_2"


def test_sos_reaches_the_feed():
    client, svc, _ = _client()
    r = client.post("/api/responder", json={"action": "sos", "responder_id": "resp_1"})
    assert r.status_code == 200 and r.json()["ok"]
    kinds = [e["kind"] for e in svc.feed]
    assert "sos" in kinds
    e = next(e for e in svc.feed if e["kind"] == "sos")
    assert e["responder_id"] == "resp_1" and e.get("name")


def test_overdue_safety_alert_fires_once():
    client, svc, sim = _client()
    r = sim._resp["resp_1"]
    # put the responder enroute and freeze them in place
    r["state"], r["order_id"], r["target"] = "enroute", "order_x", (r["lat"], r["lng"])
    r["route"], r["route_idx"] = None, 0
    sim.manual.add("resp_1")            # human-controlled: sim won't move them
    for _ in range(40):                  # > 150 sim-seconds of stillness
        sim.sim_now += 10
        sim._check_overdue(r)
    alerts = [e for e in svc.feed if e["kind"] == "safety_alert"]
    assert len(alerts) == 1              # once per order, not per tick
    assert alerts[0]["responder_id"] == "resp_1"


def test_manifest_and_sw_served():
    client, _, _ = _client()
    m = client.get("/static/manifest.webmanifest")
    assert m.status_code == 200
    data = json.loads(m.text)
    assert data["display"] == "standalone" and data["icons"]
    assert client.get("/static/sw.js").status_code == 200
    assert client.get("/static/icons/icon-192.png").status_code == 200
