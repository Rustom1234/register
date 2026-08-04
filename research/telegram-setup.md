> **Parked (founder decision, 2026-08-04):** no Telegram for now. The
> built-in web reporting page at `/witness` is the demo and test chat
> line — it drives the identical intake pipeline with zero external
> accounts. This document stays as the ready-to-go playbook if a real
> external channel is wanted later (the adapter code is built and tested,
> dormant without a token).

# Telegram chat line — setup guide

WhatsApp Business verification through Meta is stuck in the approval queue,
so the chat line launches on Telegram instead. Telegram is the instant,
free equivalent: a bot token takes about two minutes to get, there is no
business verification, no approval wait, and no per-message cost. The code
(`pukaar/telegram.py`) is a mirror of the WhatsApp adapter, so nothing
else in the system changes — a Telegram chat flows through the exact same
intake, gate, and dispatch pipeline as the demo UI.

## 1. Create the bot (one time, ~2 minutes)

1. Open Telegram and message **@BotFather** (the official bot-creation bot,
   blue verified check).
2. Send `/newbot`.
3. Pick a display name people will see, e.g. `Pukaar` (working name — swap
   for Wayside when the rename lands).
4. Pick a username ending in `bot`, e.g. `PukaarAidBot`. This fixes your
   public link: `t.me/PukaarAidBot`.
5. BotFather replies with the **bot token** — a string like
   `1234567890:AAE...xyz`. Treat it like a password: anyone holding it can
   send and read messages as the bot. Do not commit it, do not paste it in
   chat logs.

Optional polish, also via BotFather:

- `/setdescription` — one line about what the bot does ("Report a person on
  the street who needs help").
- `/setuserpic` — the Pukaar/Wayside logo.
- `/setcommands` — register `start - Report someone who needs help` so the
  command menu looks intentional.

## 2. Configure and run

The token travels only through an environment variable — never a file in
the repo:

```bash
export PUKAAR_TELEGRAM_TOKEN="1234567890:AAE...xyz"
python -m pukaar
```

With the variable set, the app starts the Telegram bridge alongside the
demo control room; without it, the bridge stays completely dormant (the
demo keeps working exactly as before). The bridge uses **long polling** —
it dials out to Telegram's servers — so there is no webhook, no public
URL, no port forwarding, and no TLS certificate to arrange. It runs fine
from a laptop behind home Wi-Fi, which is exactly the pilot posture.

If the network drops, the bridge retries with backoff (1s doubling to a
60s ceiling) and picks up where it left off; no messages are lost on
Telegram's side while it is down (updates queue for ~24h).

## 3. The poster: QR + link

The public entry point is the bot link:

```
https://t.me/PukaarAidBot
```

Tapping it opens the chat with a **Start** button; pressing Start sends
`/start`, which the bridge maps to a greeting so the witness immediately
gets the first-contact notice and the "where is the person?" flow.

For street posters, turn the link into a QR code with any generator (or
locally, no account needed):

```bash
pip install qrcode[pil]
python -c "import qrcode; qrcode.make('https://t.me/PukaarAidBot').save('poster-qr.png')"
```

Poster copy suggestion: the QR, the `t.me/PukaarAidBot` link written out
for people who cannot scan, and one line in Hindi + English: "Kisi ko
sadak par madad chahiye? Scan karein / Need help for someone on the
street? Scan."

## 4. What this costs and what it does not need

- **Free.** The Bot API has no message fees, no business account, no
  monthly cost.
- **No approval.** BotFather issues tokens instantly; there is no review
  queue and nothing to get rejected from.
- **No infrastructure.** Long polling means no server with a public IP is
  required for the pilot.
- **Same privacy posture.** The chat id is hashed the same way phone
  numbers are (it enters the pipeline as `tg:<chat_id>`); photos are not
  downloaded — only the caption travels as the photo hint.

Known limits to be honest about: witnesses need the Telegram app (far less
universal in Delhi than WhatsApp), and location shares require the witness
to tap the attach menu rather than being prompted by a native
"share location" button. The intake copy already asks for a pin or a
landmark in words, which covers the gap.

## 5. WhatsApp later — the honest paragraph

Telegram is the bridge, not the destination. The people most likely to
witness someone in need in Delhi are on WhatsApp, and the WhatsApp adapter
(`pukaar/whatsapp.py`) is finished, tested, and waiting. What blocks it is
not code: Meta requires a verified business (Business Manager
verification, a display-name review, and a phone number that is not
attached to a personal WhatsApp), and that process takes days to weeks and
can require registration paperwork an early-stage project may not have
yet. When the verification clears, the switch is configuration — set
`WA_TOKEN`/`WA_PHONE_ID` and point Meta's webhook at `/webhook` — and both
lines can run side by side during the transition. Until then, Telegram
gives us a real, free, working chat line today instead of a perfect one
someday.
