"""Cloud API webhook parsing + endpoint wiring (transport is dormant
without credentials, but the shapes are live and tested)."""

from fastapi.testclient import TestClient

from pukaar.api import build_app
from pukaar.config import Config
from pukaar.whatsapp import parse_webhook


def _wrap(*messages):
    return {"entry": [{"changes": [{"value": {"messages": list(messages)}}]}]}


def test_parse_text():
    msgs = parse_webhook(_wrap({"from": "919876543210", "type": "text",
                                "text": {"body": "aadmi ghayal hai"}}))
    assert msgs == [{"phone": "919876543210", "kind": "text", "text": "aadmi ghayal hai"}]


def test_parse_button_reply():
    msgs = parse_webhook(_wrap({"from": "91987", "type": "interactive",
                                "interactive": {"type": "button_reply",
                                                "button_reply": {"id": "cat:medical", "title": "Chot"}}}))
    assert msgs[0]["kind"] == "button" and msgs[0]["text"] == "cat:medical"


def test_parse_location():
    msgs = parse_webhook(_wrap({"from": "91987", "type": "location",
                                "location": {"latitude": 28.59, "longitude": 77.25}}))
    assert msgs[0]["kind"] == "location" and msgs[0]["lat"] == 28.59


def test_parse_image_and_audio():
    msgs = parse_webhook(_wrap(
        {"from": "91987", "type": "image", "image": {"id": "m1", "caption": "pair mein chot"}},
        {"from": "91987", "type": "audio", "audio": {"id": "m2", "voice": True}}))
    assert msgs[0] == {"phone": "91987", "kind": "photo", "media_id": "m1", "photo_hint": "pair mein chot"}
    assert msgs[1]["kind"] == "voice"


def test_parse_ignores_unsupported():
    assert parse_webhook(_wrap({"from": "x", "type": "sticker", "sticker": {}})) == []
    assert parse_webhook({}) == []


def _client():
    cfg = Config()
    cfg.backend = "mock"
    app = build_app(cfg)
    return TestClient(app)


# The webhook is inert without WA_APP_SECRET (an unsigned open endpoint would
# be a message-injection hole); a real Meta pilot always sets it. These tests
# configure the secret and sign the body the way Meta does.
import hashlib
import hmac
import json as _json
import os


def _signed_post(client, body: dict):
    secret = os.environ["WA_APP_SECRET"]
    raw = _json.dumps(body).encode()
    sig = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return client.post("/webhook", content=raw,
                       headers={"content-type": "application/json",
                                "X-Hub-Signature-256": sig})


def test_webhook_verify_roundtrip():
    with _client() as client:
        r = client.get("/webhook", params={"hub.mode": "subscribe",
                                           "hub.verify_token": "pukaar-verify",
                                           "hub.challenge": "12345"})
        assert r.status_code == 200 and r.text == "12345"
        r = client.get("/webhook", params={"hub.mode": "subscribe",
                                           "hub.verify_token": "wrong",
                                           "hub.challenge": "x"})
        assert r.status_code == 403


def test_webhook_inert_without_app_secret():
    # the default hosted/demo state (no WA_APP_SECRET) must NOT accept
    # unsigned injected messages
    os.environ.pop("WA_APP_SECRET", None)
    with _client() as client:
        r = client.post("/webhook", json=_wrap(
            {"from": "919000000000", "type": "text", "text": {"body": "x"}}))
        assert r.status_code == 403


def test_webhook_post_feeds_pipeline():
    os.environ["WA_APP_SECRET"] = "test-secret"
    try:
        with _client() as client:
            r = _signed_post(client, _wrap(
                {"from": "919876543210", "type": "text", "text": {"body": "ek aadmi ghayal hai"}}))
            assert r.status_code == 200
            assert r.json() == {"handled": 1, "sending": False}
            state = client.get("/api/state").json()
            assert any("919876" in p for p in state["conversations"])
    finally:
        del os.environ["WA_APP_SECRET"]


def test_webhook_voice_flows_as_voice_kind():
    os.environ["WA_APP_SECRET"] = "test-secret"
    try:
        with _client() as client:
            r = _signed_post(client, _wrap(
                {"from": "919812345678", "type": "audio", "audio": {"id": "m9", "voice": True}}))
            assert r.status_code == 200 and r.json()["handled"] == 1
            state = client.get("/api/state").json()
            conv = next(v for k, v in state["conversations"].items() if "919812" in k)
            assert conv[0]["kind"] == "voice"
            assert conv[0]["text"].startswith("🎤")
    finally:
        del os.environ["WA_APP_SECRET"]
