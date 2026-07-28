"""`python -m pukaar` — run the demo control room."""

from __future__ import annotations

import os

import uvicorn

from .api import build_app
from .config import Config


def main() -> None:
    cfg = Config()
    host = os.environ.get("PUKAAR_HOST", "127.0.0.1")
    port = int(os.environ.get("PUKAAR_PORT", "8877"))
    # Refuse a non-local bind without a persistent provenance key — hosting
    # the demo publicly with an ephemeral key silently voids the audit
    # trail. PUKAAR_ALLOW_INSECURE=1 overrides for throwaway demos.
    if host not in ("127.0.0.1", "localhost", "::1") and not cfg.hmac_key \
            and not os.environ.get("PUKAAR_ALLOW_INSECURE"):
        raise SystemExit(
            f"Refusing to bind {host} without PUKAAR_HMAC_KEY. Set a key, or "
            "set PUKAAR_ALLOW_INSECURE=1 for a throwaway demo.")
    print(f"Pukaar demo · backend={cfg.resolve_backend()} · http://{host}:{port}")
    uvicorn.run(build_app(cfg), host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
