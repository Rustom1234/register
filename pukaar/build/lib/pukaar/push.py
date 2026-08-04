"""Web Push for the responder app.

Real push (phone buzzes with the app closed) rides the browser vendors'
push services via pywebpush + self-generated VAPID keys — no third-party
account, no paid API. The keypair is generated at first boot and kept in
the database, subscriptions arrive from the responder app's service
worker, and every send is fire-and-forget on a daemon thread: a dead or
unreachable push endpoint (offline demo, sandbox, expired subscription)
must never slow or break dispatch.
"""

from __future__ import annotations

import base64
import json
import threading

try:
    from py_vapid import Vapid
    from pywebpush import WebPushException, webpush
    _PUSH_OK = True
except Exception:                                    # pragma: no cover
    _PUSH_OK = False


class PushService:
    def __init__(self, store):
        self.store = store
        self._pem: str | None = None
        self._pub: str | None = None
        if _PUSH_OK:
            self._load_or_create_keys()

    # ------------------------------------------------------------- keys --
    def _load_or_create_keys(self) -> None:
        row = self.store.one("SELECT v FROM push_meta WHERE k='vapid_pem'")
        if row:
            pem = row["v"]
            vapid = Vapid.from_pem(pem.encode())
        else:
            vapid = Vapid()
            vapid.generate_keys()
            pem = vapid.private_pem().decode()
            self.store.execute(
                "INSERT OR REPLACE INTO push_meta (k, v) VALUES ('vapid_pem', ?)", (pem,))
        self._pem = pem
        from cryptography.hazmat.primitives import serialization
        raw = vapid.public_key.public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        self._pub = base64.urlsafe_b64encode(raw).decode().rstrip("=")

    def vapid_public_key(self) -> str | None:
        """The applicationServerKey the browser needs — None when the push
        stack isn't available (push then falls back to in-page alerts)."""
        return self._pub

    # ---------------------------------------------------------- storage --
    def subscribe(self, responder_id: str, subscription: dict) -> None:
        endpoint = (subscription or {}).get("endpoint", "")
        if not endpoint:
            return
        self.store.execute(
            "INSERT OR REPLACE INTO push_subs (endpoint, responder_id, sub) VALUES (?, ?, ?)",
            (endpoint, responder_id, json.dumps(subscription)))

    # ------------------------------------------------------------- send --
    def notify(self, responder_id: str, title: str, body: str, url: str = "/responder") -> None:
        """Send a push to every subscription this responder has. Never
        raises; never blocks the caller."""
        if not (_PUSH_OK and self._pem):
            return
        subs = self.store.query(
            "SELECT endpoint, sub FROM push_subs WHERE responder_id=?", (responder_id,))
        if not subs:
            return
        payload = json.dumps({"title": title, "body": body, "url": url})
        threading.Thread(target=self._send_all, args=(subs, payload), daemon=True).start()

    def _send_all(self, subs: list[dict], payload: str) -> None:
        for row in subs:
            try:
                webpush(
                    subscription_info=json.loads(row["sub"]),
                    data=payload,
                    vapid_private_key=self._pem,
                    vapid_claims={"sub": "mailto:demo@wayside.invalid"},
                    timeout=6,
                )
            except WebPushException as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status in (404, 410):             # subscription is dead — drop it
                    try:
                        self.store.execute("DELETE FROM push_subs WHERE endpoint=?",
                                           (row["endpoint"],))
                    except Exception:
                        pass
            except Exception:
                pass                                 # offline / blocked egress: fine
