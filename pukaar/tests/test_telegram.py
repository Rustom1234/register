"""Telegram bridge: pure update mapping + one mocked long-poll cycle.

Everything runs offline — the transport is httpx.MockTransport, so
api.telegram.org is never touched (the sandbox can't reach it anyway).
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest

from pukaar.telegram import (BACKOFF_START_S, TelegramBridge, reply_payload,
                             update_to_inbound)


def _msg(update_id=1, **message):
    return {"update_id": update_id, "message": {"chat": {"id": 42}, **message}}


# ------------------------------------------------- update_to_inbound -----

def test_text_message_maps_to_text_kind():
    got = update_to_inbound(_msg(text="aadmi ghayal hai"))
    assert got == {"phone": "tg:42", "kind": "text", "text": "aadmi ghayal hai"}


def test_chat_id_becomes_tg_prefixed_phone():
    got = update_to_inbound({"update_id": 9,
                             "message": {"chat": {"id": -100123}, "text": "hi"}})
    assert got["phone"] == "tg:-100123"


def test_start_command_maps_to_greeting_text():
    got = update_to_inbound(_msg(text="/start"))
    assert got["kind"] == "text" and got["text"] == "namaste"
    # deep-link and @BotName forms too
    assert update_to_inbound(_msg(text="/start@PukaarBot"))["text"] == "namaste"
    assert update_to_inbound(_msg(text="/start ref_poster1"))["text"] == "namaste"


def test_location_share_maps_to_location_kind():
    got = update_to_inbound(_msg(location={"latitude": 28.59, "longitude": 77.25}))
    assert got == {"phone": "tg:42", "kind": "location", "lat": 28.59, "lng": 77.25}


def test_photo_uses_caption_as_hint():
    got = update_to_inbound(_msg(photo=[{"file_id": "f1"}], caption="pair mein chot"))
    assert got == {"phone": "tg:42", "kind": "photo", "photo_hint": "pair mein chot"}


def test_photo_without_caption_gets_default_hint():
    got = update_to_inbound(_msg(photo=[{"file_id": "f1"}]))
    assert got["kind"] == "photo" and got["photo_hint"] == "witness photo"


def test_callback_query_maps_to_button_kind():
    got = update_to_inbound({
        "update_id": 5,
        "callback_query": {"id": "cb1", "data": "cat:medical",
                           "message": {"chat": {"id": 42}}}})
    assert got == {"phone": "tg:42", "kind": "button", "text": "cat:medical"}


def test_malformed_updates_return_none():
    assert update_to_inbound(None) is None
    assert update_to_inbound("junk") is None
    assert update_to_inbound({}) is None
    assert update_to_inbound({"update_id": 1}) is None
    assert update_to_inbound({"update_id": 1, "message": "not-a-dict"}) is None
    # message without a chat id
    assert update_to_inbound({"update_id": 1, "message": {"text": "hi"}}) is None
    # callback_query missing data / missing chat
    assert update_to_inbound({"callback_query": {"id": "x",
                                                 "message": {"chat": {"id": 1}}}}) is None
    assert update_to_inbound({"callback_query": {"id": "x", "data": "d"}}) is None
    # location without coordinates
    assert update_to_inbound(_msg(location={})) is None


def test_unsupported_kinds_ignored():
    assert update_to_inbound(_msg(sticker={"emoji": "🙏"})) is None
    assert update_to_inbound(_msg(voice={"file_id": "v1"})) is None
    assert update_to_inbound(_msg(text="   ")) is None
    # edited messages carry no "message" key -> ignored
    assert update_to_inbound({"update_id": 2,
                              "edited_message": {"chat": {"id": 42},
                                                 "text": "edit"}}) is None


# ----------------------------------------------------- reply_payload -----

def test_reply_payload_plain_text():
    got = reply_payload(42, "Namaste 🙏")
    assert got == {"chat_id": 42, "text": "Namaste 🙏"}


def test_reply_payload_builds_inline_keyboard():
    got = reply_payload("42", "Ek chunein:", [
        {"id": "cat:medical", "label": "Chot / bimar"},
        {"id": "cat:food", "label": "Bhookh"}])
    kb = got["reply_markup"]["inline_keyboard"]
    assert kb == [[{"text": "Chot / bimar", "callback_data": "cat:medical"}],
                  [{"text": "Bhookh", "callback_data": "cat:food"}]]


def test_reply_payload_truncates_text_and_callback_data():
    got = reply_payload(1, "x" * 5000, [{"id": "i" * 100, "label": "l" * 100}])
    assert len(got["text"]) == 4096
    btn = got["reply_markup"]["inline_keyboard"][0][0]
    assert len(btn["callback_data"]) == 64 and len(btn["text"]) == 64


# ----------------------------------------------------------- bridge ------

class StubSvc:
    """Records wa_inbound calls; answers like the real service (BotMsg shape)."""

    def __init__(self, replies=None):
        self.calls = []
        self.replies = replies if replies is not None else [SimpleNamespace(
            text="Kya zaroorat dikh rahi hai? Ek chunein:",
            buttons=[{"id": "cat:medical", "label": "Chot"},
                     {"id": "cat:food", "label": "Bhookh"}],
            string_id="S-ASK-CATEGORY")]

    def wa_inbound(self, phone, kind, text=None, lat=None, lng=None,
                   photo_hint=None):
        self.calls.append({"phone": phone, "kind": kind, "text": text,
                           "lat": lat, "lng": lng, "photo_hint": photo_hint})
        return self.replies


def _mock_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_bridge_requires_token():
    with pytest.raises(ValueError):
        TelegramBridge("", StubSvc())


def test_poll_cycle_end_to_end():
    """One getUpdates round: text update in -> stub svc -> sendMessage out."""
    sent, polls = [], []

    def handler(request):
        path = request.url.path
        if path.endswith("/getUpdates"):
            polls.append(dict(request.url.params))
            return httpx.Response(200, json={"ok": True, "result": [
                {"update_id": 7,
                 "message": {"chat": {"id": 4242}, "text": "ek aadmi ghayal hai"}}]})
        if path.endswith("/sendMessage"):
            sent.append(json.loads(request.content))
            return httpx.Response(200, json={"ok": True, "result": {}})
        raise AssertionError(f"unexpected call: {path}")

    svc = StubSvc()
    bridge = TelegramBridge("123:TEST", svc, client=_mock_client(handler))
    assert bridge.poll_once() == 1

    # inbound reached the service in wa_inbound shape, tg: phone included
    assert svc.calls == [{"phone": "tg:4242", "kind": "text",
                          "text": "ek aadmi ghayal hai", "lat": None,
                          "lng": None, "photo_hint": None}]
    # the service reply went out as a sendMessage with an inline keyboard
    assert len(sent) == 1
    assert sent[0]["chat_id"] == "4242"
    assert sent[0]["text"].startswith("Kya zaroorat")
    kb = sent[0]["reply_markup"]["inline_keyboard"]
    assert kb[0][0]["callback_data"] == "cat:medical"
    # offset advanced past the consumed update
    assert bridge.offset == 8
    # next poll would ask from the new offset (regression guard on ack)
    bridge.svc = StubSvc([])
    bridge.poll_once()
    assert polls[-1]["offset"] == "8"


def test_button_press_acks_and_flows_as_button_kind():
    acked, sent = [], []

    def handler(request):
        path = request.url.path
        if path.endswith("/getUpdates"):
            return httpx.Response(200, json={"ok": True, "result": [
                {"update_id": 3,
                 "callback_query": {"id": "cbq-1", "data": "cat:food",
                                    "message": {"chat": {"id": 55}}}}]})
        if path.endswith("/answerCallbackQuery"):
            acked.append(json.loads(request.content))
            return httpx.Response(200, json={"ok": True, "result": True})
        if path.endswith("/sendMessage"):
            sent.append(json.loads(request.content))
            return httpx.Response(200, json={"ok": True, "result": {}})
        raise AssertionError(f"unexpected call: {path}")

    svc = StubSvc([SimpleNamespace(text="Shukriya", buttons=[], string_id="")])
    bridge = TelegramBridge("123:TEST", svc, client=_mock_client(handler))
    bridge.poll_once()

    assert acked == [{"callback_query_id": "cbq-1"}]
    assert svc.calls[0]["phone"] == "tg:55" and svc.calls[0]["kind"] == "button"
    assert svc.calls[0]["text"] == "cat:food"
    assert sent[0] == {"chat_id": "55", "text": "Shukriya"}


def test_malformed_updates_do_not_break_the_cycle():
    """Junk in the same batch as a good update: junk skipped, good handled,
    offset still advances over everything."""
    def handler(request):
        if request.url.path.endswith("/getUpdates"):
            return httpx.Response(200, json={"ok": True, "result": [
                {"update_id": 10},                                   # empty
                {"update_id": 11, "message": {"text": "no chat"}},   # malformed
                {"update_id": 12,
                 "message": {"chat": {"id": 7}, "text": "hi"}}]})
        return httpx.Response(200, json={"ok": True, "result": {}})

    svc = StubSvc([])
    bridge = TelegramBridge("123:TEST", svc, client=_mock_client(handler))
    bridge.poll_once()
    assert [c["phone"] for c in svc.calls] == ["tg:7"]
    assert bridge.offset == 13


def test_run_backs_off_on_transport_error_then_recovers(monkeypatch):
    """First poll blows up (network), run() sleeps and retries; the second
    poll delivers an update whose handling stops the loop."""
    calls = {"n": 0}
    sleeps = []

    def handler(request):
        if request.url.path.endswith("/getUpdates"):
            calls["n"] += 1
            if calls["n"] == 1:
                raise httpx.ConnectError("net down", request=request)
            return httpx.Response(200, json={"ok": True, "result": [
                {"update_id": 1, "message": {"chat": {"id": 9}, "text": "hi"}}]})
        return httpx.Response(200, json={"ok": True, "result": {}})

    class StopSvc(StubSvc):
        def wa_inbound(self, *a, **kw):
            bridge.running = False           # end the test loop
            return super().wa_inbound(*a, **kw)

    svc = StopSvc([])
    bridge = TelegramBridge("123:TEST", svc, client=_mock_client(handler))
    monkeypatch.setattr("pukaar.telegram.time.sleep", sleeps.append)
    bridge.run()

    assert sleeps == [BACKOFF_START_S]       # exactly one backoff sleep
    assert calls["n"] == 2                   # errored once, recovered once
    assert svc.calls[0]["phone"] == "tg:9"
