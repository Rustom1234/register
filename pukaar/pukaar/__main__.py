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
    # Going live on WhatsApp without webhook signature verification means
    # anyone who finds the URL can forge witness messages — refuse the
    # half-configured state instead of silently accepting it.
    if os.environ.get("WA_TOKEN") and not os.environ.get("WA_APP_SECRET") \
            and not os.environ.get("PUKAAR_ALLOW_INSECURE"):
        raise SystemExit(
            "WA_TOKEN is set but WA_APP_SECRET is not: outbound WhatsApp would go "
            "live with webhook signature checks disabled. Set WA_APP_SECRET (Meta "
            "app dashboard → App settings → Basic), or PUKAAR_ALLOW_INSECURE=1 "
            "for a throwaway test.")
    # The other half-configured state: token without a phone id means the
    # webhook happily ACCEPTS witness messages while every reply silently
    # fails to send — worse than being down, because nobody notices.
    if os.environ.get("WA_TOKEN") and not os.environ.get("WA_PHONE_ID"):
        raise SystemExit(
            "WA_TOKEN is set but WA_PHONE_ID is not: inbound messages would be "
            "accepted while every outbound reply fails. Set WA_PHONE_ID (Meta "
            "app dashboard → WhatsApp → API Setup), or unset WA_TOKEN.")

    if host not in ("127.0.0.1", "localhost", "::1") and not cfg.admin_token:
        print("WARNING: binding publicly with no PUKAAR_ADMIN_TOKEN — every "
              "surface, live chat, and export is open to anyone with the URL.")

    print(f"Wayside demo · backend={cfg.resolve_backend()} · http://{host}:{port}")
    app = build_app(cfg)

    # Optional Telegram chat line (the WhatsApp-equivalent that needs no
    # Meta verification): set PUKAAR_TELEGRAM_TOKEN and the bridge long-polls
    # in a daemon thread. Absent a token it never even imports the module.
    tg_token = os.environ.get("PUKAAR_TELEGRAM_TOKEN", "").strip()
    if tg_token:
        import threading

        from .telegram import TelegramBridge

        bridge = TelegramBridge(tg_token, app.state.svc)
        # Fail loud, not silent: a revoked/typo'd token must be visible at
        # boot — but a DNS blip at container start is NOT a revoked token,
        # and the bridge's own backoff loop handles a network that comes up
        # a few seconds after we do.
        status, me = bridge.probe()
        if status == "rejected":
            print("WARNING: PUKAAR_TELEGRAM_TOKEN was rejected by Telegram "
                  "(bad/revoked token) — the bridge is NOT running.")
        else:
            threading.Thread(target=bridge.run, daemon=True).start()
            if status == "ok":
                print(f"Telegram bridge: polling as @{me} (witnesses can message the bot)")
            else:
                print("Telegram bridge: couldn't reach api.telegram.org at boot — "
                      "starting anyway; the poll loop retries with backoff.")

    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
