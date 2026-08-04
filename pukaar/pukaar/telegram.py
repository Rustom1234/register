"""Telegram Bot API transport — the instant, free stand-in for WhatsApp.

The founder deferred Meta/WhatsApp Business verification, so the chat line
ships on Telegram first: BotFather issues a token in two minutes, there is
no approval queue, no per-message fee, and long polling means no public
webhook URL is needed — the bridge dials out, so it runs from any laptop.

Mirror image of `whatsapp.py`, same split:

- `update_to_inbound()` / `reply_payload()` — pure mapping functions that
  normalize Telegram updates into the (phone, kind, ...) shape
  `service.wa_inbound()` already speaks, and turn the service's
  {text, buttons:[{id,label}]} replies into sendMessage payloads with
  inline keyboards. Fully unit-tested offline.
- `TelegramBridge` — the long-poll loop (getUpdates -> service -> reply).
  DORMANT by design: nothing here runs at import time; the bridge is only
  constructed when PUKAAR_TELEGRAM_TOKEN is configured, and refuses to
  exist without a token.

Wire notes locked in from the Bot API docs: message text caps at 4096
chars; callback_data caps at 64 bytes (our button ids like "cat:medical"
fit easily); a tapped inline button spins until answerCallbackQuery, so
the bridge always acks; chat ids are integers and become the pipeline's
"phone" as f"tg:{chat_id}" so hashing/rate-limiting work unchanged.
"""

from __future__ import annotations

import time
from typing import Any

API = "https://api.telegram.org"

# Long-poll tuning: Telegram holds getUpdates open up to `POLL_S` seconds;
# the HTTP client timeout must sit above that or every quiet minute looks
# like a network error.
POLL_S = 50
HTTP_TIMEOUT_S = POLL_S + 10
BACKOFF_START_S = 1.0
BACKOFF_MAX_S = 60.0


# --------------------------------------------------------- pure mapping ---

def update_to_inbound(update: Any) -> dict | None:
    """Telegram update -> {phone, kind, text?, lat?, lng?, photo_hint?} or None.

    None means "nothing for the pipeline" (edits, stickers, joins, malformed
    junk) — the caller just advances the offset and moves on. Never raises
    on bad shapes: a hostile or truncated update must not kill the poll loop.
    """
    if not isinstance(update, dict):
        return None

    # Inline-keyboard button press arrives as a callback_query, not a message.
    cb = update.get("callback_query")
    if isinstance(cb, dict):
        msg = cb.get("message")
        chat = msg.get("chat") if isinstance(msg, dict) else None
        chat_id = chat.get("id") if isinstance(chat, dict) else None
        data = cb.get("data")
        if chat_id is None or not isinstance(data, str) or not data:
            return None
        return {"phone": f"tg:{chat_id}", "kind": "button", "text": data}

    msg = update.get("message")
    if not isinstance(msg, dict):
        return None
    chat = msg.get("chat")
    chat_id = chat.get("id") if isinstance(chat, dict) else None
    if chat_id is None:
        return None
    phone = f"tg:{chat_id}"

    loc = msg.get("location")
    if isinstance(loc, dict):
        lat, lng = loc.get("latitude"), loc.get("longitude")
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            return None
        return {"phone": phone, "kind": "location",
                "lat": float(lat), "lng": float(lng)}

    if msg.get("photo"):
        # We deliberately do not download the file — same privacy stance as
        # the demo: only the caption travels as the photo_hint.
        caption = msg.get("caption")
        hint = caption if isinstance(caption, str) and caption.strip() else "witness photo"
        return {"phone": phone, "kind": "photo", "photo_hint": hint}

    text = msg.get("text")
    if isinstance(text, str) and text.strip():
        first = text.strip().split()[0].split("@")[0].lower()
        if first == "/start":
            # /start is what tapping the poster's t.me link sends. Ride the
            # normal first-message path so the S-NOTICE greeting fires.
            return {"phone": phone, "kind": "text", "text": "namaste"}
        return {"phone": phone, "kind": "text", "text": text}

    return None  # voice/sticker/contact/etc. — ignored on purpose (P1: STT)


def reply_payload(chat_id: Any, text: str, buttons: list[dict] | None = None) -> dict:
    """Service reply -> sendMessage payload. Buttons ({id,label}) become an
    inline keyboard, one per row (big tap targets on cheap phones)."""
    payload: dict = {"chat_id": chat_id, "text": (text or "")[:4096]}
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": [
            [{"text": str(b["label"])[:64], "callback_data": str(b["id"])[:64]}]
            for b in buttons
        ]}
    return payload


# -------------------------------------------------------------- bridge ---

class TelegramBridge:
    """Long-poll bridge: getUpdates -> service.wa_inbound -> sendMessage.

    Construct only with a real token (the __main__/config wiring guards
    this); `client` is injectable so tests run on httpx.MockTransport
    without ever touching api.telegram.org.
    """

    def __init__(self, token: str, svc, client=None) -> None:
        if not token:
            raise ValueError("TelegramBridge needs a bot token "
                             "(set PUKAAR_TELEGRAM_TOKEN); it must stay "
                             "dormant otherwise")
        self.token = token
        self.svc = svc
        self.base = f"{API}/bot{token}"
        if client is None:                       # lazy: keep import cheap
            import httpx
            client = httpx.Client(timeout=HTTP_TIMEOUT_S)
        self.client = client
        self.offset = 0          # next update_id to ask for
        self.running = True      # flip False to stop run()
        self._retries: dict[int, int] = {}   # update_id -> failed attempts

    # ------------------------------------------------------------- send --
    def send_reply(self, chat_id: Any, text: str,
                   buttons: list[dict] | None = None) -> dict:
        """Send one reply; returns the payload that went over the wire."""
        payload = reply_payload(chat_id, text, buttons)
        r = self.client.post(f"{self.base}/sendMessage", json=payload)
        r.raise_for_status()
        return payload

    def _ack_callback(self, callback_id: str) -> None:
        """Stop the inline button's spinner. Best-effort: a failed ack must
        not lose the witness's reply."""
        try:
            self.client.post(f"{self.base}/answerCallbackQuery",
                             json={"callback_query_id": callback_id})
        except Exception:
            pass

    # ---------------------------------------------------------- inbound --
    def handle_update(self, update: dict) -> None:
        """One update through the pipeline; replies go straight back out.
        Offset confirmation lives in poll_once — confirming BEFORE the reply
        went out meant one transient sendMessage failure silently dropped a
        witness's message forever."""
        inbound = update_to_inbound(update)
        if inbound is None:
            return
        cb = update.get("callback_query")
        if isinstance(cb, dict) and cb.get("id"):
            self._ack_callback(cb["id"])
        chat_id = inbound["phone"].split(":", 1)[1]
        replies = self.svc.wa_inbound(
            inbound["phone"], inbound["kind"],
            text=inbound.get("text"),
            lat=inbound.get("lat"), lng=inbound.get("lng"),
            photo_hint=inbound.get("photo_hint"))
        for r in replies:
            self.send_reply(chat_id, r.text, r.buttons)

    def check(self) -> str | None:
        """Validate the token against getMe. Returns the bot's username on
        success, None otherwise (see probe() for the distinction boot needs)."""
        status, name = self.probe()
        return name if status == "ok" else None

    def probe(self) -> tuple[str, str | None]:
        """getMe with a three-way answer: ('ok', username) — token works;
        ('rejected', None) — Telegram said no, the token is bad/revoked;
        ('network', None) — couldn't reach Telegram at all. Boot must treat
        these differently: a DNS blip at container start is not a revoked
        token, and permanently disabling the bridge over one is a silent
        outage that looks identical to 'nobody messaged us'."""
        try:
            r = self.client.get(f"{self.base}/getMe")
            body = r.json()
            if r.status_code == 200 and body.get("ok"):
                return "ok", (body.get("result") or {}).get("username") or "unknown"
            return "rejected", None
        except Exception:
            return "network", None

    def poll_once(self) -> int:
        """One getUpdates round trip; returns how many updates were handled."""
        r = self.client.get(
            f"{self.base}/getUpdates",
            params={"offset": self.offset, "timeout": POLL_S,
                    "allowed_updates": '["message","callback_query"]'})
        r.raise_for_status()
        body = r.json()
        updates = body.get("result") if body.get("ok") else None
        if not isinstance(updates, list):
            return 0
        for u in updates:
            uid = u.get("update_id") if isinstance(u, dict) else None
            try:
                self.handle_update(u)
            except Exception:
                # At-least-once: don't confirm — leave offset put so this
                # update redelivers after run()'s backoff. Bounded so one
                # poison update can't wedge the line: 3 tries, then skip
                # loudly. (Malformed updates never raise — they're consumed
                # and confirmed like any other.)
                if isinstance(uid, int):
                    n = self._retries[uid] = self._retries.get(uid, 0) + 1
                    if n < 3:
                        raise
                    print(f"[telegram] giving up on update {uid} after {n} attempts")
                else:
                    raise
            if isinstance(uid, int):
                self.offset = max(self.offset, uid + 1)
                self._retries.pop(uid, None)
        return len(updates)

    def run(self) -> None:
        """Poll forever with exponential backoff on transport errors.

        Telegram's long poll returns empty after POLL_S quiet seconds, so
        the happy path loops without sleeping; only failures back off
        (1s -> 2s -> ... -> 60s), and one good poll resets the clock."""
        backoff = BACKOFF_START_S
        while self.running:
            try:
                self.poll_once()
                backoff = BACKOFF_START_S
            except Exception:
                time.sleep(backoff)
                backoff = min(backoff * 2, BACKOFF_MAX_S)
