"""Runtime configuration.

Model choices follow the approved build plan (research/build-plan.md §2):
a cheap fast model for the intake conversation, a stronger model for
photo assist / routing / order generation. Both are overridable by env.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass
class Config:
    # Backend: "auto" uses Claude when a credential is likely present, else mock.
    backend: str = field(default_factory=lambda: _env("PUKAAR_BACKEND", "auto"))
    model_intake: str = field(default_factory=lambda: _env("PUKAAR_MODEL_INTAKE", "claude-haiku-4-5"))
    model_reasoning: str = field(default_factory=lambda: _env("PUKAAR_MODEL_REASONING", "claude-sonnet-4-6"))

    db_path: str = field(default_factory=lambda: _env("PUKAAR_DB", "pukaar-demo.db"))
    hmac_key: str = field(default_factory=lambda: _env("PUKAAR_HMAC_KEY", ""))

    # Dispatch (times are in *sim seconds*; the sim clock maps them to real time)
    offer_ttl_s: int = 180          # per-wave accept window
    max_waves: int = 3
    wave_size_p1: int = 3           # GoodSAM-style parallel offer sizes
    wave_size_default: int = 2
    responder_open_cap: int = 3     # max open orders per responder
    arrive_radius_m: float = 35.0

    # Night mode (build plan §3.12): dispatch honors partner shift windows;
    # intake stays 24/7 with honest fixed strings.
    dispatch_open_h: int = 7
    dispatch_close_h: int = 21

    # Dedup (build plan §3.6): ~150m grid + 12h window
    dedup_cell_m: float = 150.0
    dedup_window_s: int = 12 * 3600

    # Retention (build plan §4): sim-time TTLs, enforced by the purge job
    media_ttl_s: int = 72 * 3600
    latlng_ttl_s: int = 7 * 24 * 3600
    case_row_ttl_s: int = 90 * 24 * 3600

    # Simulation
    sim_speed: float = 6.0          # sim seconds per real second
    zone_lat: float = 28.5933      # Nizamuddin, Delhi
    zone_lng: float = 77.2507
    zone_radius_m: float = 1500.0

    def resolve_backend(self) -> str:
        if self.backend in ("mock", "claude"):
            return self.backend
        # auto: prefer Claude when an explicit key is present; the SDK can also
        # resolve OAuth profiles, but for demo determinism we only auto-enable
        # on an explicit env credential.
        if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
            return "claude"
        return "mock"
