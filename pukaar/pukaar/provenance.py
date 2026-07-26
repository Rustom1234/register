"""Channel provenance (memsub pattern, build plan §4).

Every record that carries information is HMAC-tagged with the channel that
produced it — `witness`, `agent_inferred`, or `responder_observed` — so an
agent's guess can never masquerade as something a human said, and audits
can reconstruct why the system believed what it believed.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets

CHANNELS = {"witness", "agent_inferred", "responder_observed", "system"}


class Provenance:
    def __init__(self, key: str | None = None):
        # Demo convenience: an ephemeral key is generated when none is
        # configured, and the UI surfaces that fact. Production requires a
        # persistent key (env/KMS) — verification breaks across restarts
        # otherwise, by design.
        self.ephemeral = not key
        self._key = (key or secrets.token_hex(32)).encode()

    def sign(self, channel: str, payload: dict) -> str:
        if channel not in CHANNELS:
            raise ValueError(f"unknown provenance channel: {channel}")
        msg = json.dumps({"channel": channel, "payload": payload}, sort_keys=True, ensure_ascii=False)
        return hmac.new(self._key, msg.encode(), hashlib.sha256).hexdigest()

    def verify(self, channel: str, payload: dict, mac: str) -> bool:
        try:
            expected = self.sign(channel, payload)
        except ValueError:
            return False
        return hmac.compare_digest(expected, mac)
