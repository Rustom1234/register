"""`python -m pukaar` — run the demo control room."""

from __future__ import annotations

import os

import uvicorn

from .api import build_app
from .config import Config


def main() -> None:
    cfg = Config()
    port = int(os.environ.get("PUKAAR_PORT", "8877"))
    print(f"Pukaar demo · backend={cfg.resolve_backend()} · http://127.0.0.1:{port}")
    uvicorn.run(build_app(cfg), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
