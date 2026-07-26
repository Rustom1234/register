"""WhatsApp Cloud API transport (build plan P1).

Two halves:
- `parse_webhook()` — normalizes Meta's webhook payload into the same
  (phone, kind, ...) shape the demo UI posts, so `service.wa_inbound()`
  is transport-agnostic. Pure function, fully tested offline.
- `CloudApi` — outbound sender (text, reply buttons, location request)
  and media download. Dormant unless WA_TOKEN + WA_PHONE_ID are set;
  the demo runs without it, the pilot flips it on with env vars.

Notes from the platform research locked in here: media download URLs
expire in ~5 minutes (download immediately); reply buttons max 3; the
witness-initiated flow rides the free 24h service window.
"""

from __future__ import annotations

import os
from typing import Any

GRAPH = "https://graph.facebook.com/v20.0"


def parse_webhook(payload: dict) -> list[dict]:
    """Meta webhook -> [{phone, kind, text?, lat?, lng?, media_id?, photo_hint?}]."""
    out: list[dict] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                phone = msg.get("from", "")
                mtype = msg.get("type")
                if mtype == "text":
                    out.append({"phone": phone, "kind": "text",
                                "text": msg.get("text", {}).get("body", "")})
                elif mtype == "interactive":
                    inter = msg.get("interactive", {})
                    reply = inter.get("button_reply") or inter.get("list_reply") or {}
                    out.append({"phone": phone, "kind": "button", "text": reply.get("id", "")})
                elif mtype == "location":
                    loc = msg.get("location", {})
                    out.append({"phone": phone, "kind": "location",
                                "lat": loc.get("latitude"), "lng": loc.get("longitude")})
                elif mtype == "image":
                    img = msg.get("image", {})
                    out.append({"phone": phone, "kind": "photo",
                                "media_id": img.get("id"),
                                "photo_hint": img.get("caption") or "witness photo"})
                elif mtype == "audio":
                    aud = msg.get("audio", {})
                    out.append({"phone": phone, "kind": "voice", "media_id": aud.get("id")})
                # unsupported types (stickers, contacts, ...) are ignored on purpose
    return out


class CloudApi:
    def __init__(self) -> None:
        self.token = os.environ.get("WA_TOKEN", "")
        self.phone_id = os.environ.get("WA_PHONE_ID", "")
        self.verify_token = os.environ.get("WA_VERIFY_TOKEN", "pukaar-verify")

    @property
    def configured(self) -> bool:
        return bool(self.token and self.phone_id)

    # ------------------------------------------------------------ send ---
    def _post(self, payload: dict) -> dict:
        import httpx

        r = httpx.post(
            f"{GRAPH}/{self.phone_id}/messages",
            headers={"Authorization": f"Bearer {self.token}"},
            json=payload, timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def send_text(self, to: str, body: str) -> dict:
        return self._post({"messaging_product": "whatsapp", "to": to,
                           "type": "text", "text": {"body": body[:4096]}})

    def send_buttons(self, to: str, body: str, buttons: list[dict]) -> dict:
        # Cloud API caps reply buttons at 3 — our category picker fits exactly.
        btns = [{"type": "reply", "reply": {"id": b["id"], "title": b["label"][:20]}}
                for b in buttons[:3]]
        return self._post({
            "messaging_product": "whatsapp", "to": to, "type": "interactive",
            "interactive": {"type": "button", "body": {"text": body[:1024]},
                            "action": {"buttons": btns}},
        })

    def send_location_request(self, to: str, body: str) -> dict:
        return self._post({
            "messaging_product": "whatsapp", "to": to, "type": "interactive",
            "interactive": {"type": "location_request_message",
                            "body": {"text": body[:1024]},
                            "action": {"name": "send_location"}},
        })

    def reply(self, to: str, bot_msg) -> dict:
        """Route a BotMsg through the right message shape."""
        if bot_msg.string_id == "S-ASK-LOCATION":
            return self.send_location_request(to, bot_msg.text)
        if bot_msg.buttons:
            return self.send_buttons(to, bot_msg.text, bot_msg.buttons)
        return self.send_text(to, bot_msg.text)

    # ----------------------------------------------------------- media ---
    def download_media(self, media_id: str) -> bytes:
        """Two-step fetch; the signed URL expires in ~5 minutes, so callers
        must invoke this inside the webhook handler, never later."""
        import httpx

        meta = httpx.get(f"{GRAPH}/{media_id}",
                         headers={"Authorization": f"Bearer {self.token}"}, timeout=15)
        meta.raise_for_status()
        url = meta.json()["url"]
        blob = httpx.get(url, headers={"Authorization": f"Bearer {self.token}"}, timeout=30)
        blob.raise_for_status()
        return blob.content
