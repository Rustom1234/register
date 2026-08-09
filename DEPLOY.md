# Deploying Wayside — the cheapest real setups

## Why not GitHub Pages

GitHub Pages serves static files — a brochure. Wayside is a running
program: it must be awake 24/7 to receive webhook calls from
WhatsApp/Telegram, keep a database, run the dispatch engine, and answer
witnesses in seconds. Pages cannot receive a POST, run Python, or store
anything. The cheapest things that CAN run it are below — one of them is
also ₹0/month.

## The three tiers

| Tier | Cost | What you get | Honest limits |
|---|---|---|---|
| **Render free** (this repo has one-click `render.yaml`) | **₹0/mo** | Full app at `https://wayside-xxxx.onrender.com` | Sleeps after ~15 idle min (first visitor waits ~1 min — a free cron-job.org pinger on `/health` keeps it awake); database resets on each deploy/restart |
| **Small VM** (Hetzner CX22, or Oracle's always-free ARM VM at ₹0 with a fiddlier signup) | ~₹350–400/mo (Hetzner) | A real 24/7 server, persistent database, no sleeping | You run `docker run` once and update it yourself |
| **Railway / Fly.io** | ~₹420/mo ($5) | Managed like Render, no sleeping, persistent volume | Card required |

**Recommendation:** demo investors on Render free today; the day a real
pilot starts, move to the ₹350 VM (same Docker image, zero code changes).

## Deploy to Render in ~10 minutes

1. Push this repo to your own GitHub (already done if you're reading this
   on your fork).
2. [render.com](https://render.com) → **New → Blueprint** → pick the repo.
   Render reads `render.yaml` and builds the Docker image.
3. In the service's **Environment** tab, paste your secrets (these are the
   only manual ones — see the table below). **The Anthropic key goes here
   and only here — never into a file, never into git.**
4. Deploy. Open `https://<your-app>.onrender.com` — the control room.
   `/responder` on a phone is the rider app; `/witness` is the chat.
5. Keep it awake: [cron-job.org](https://cron-job.org) (free) → new job →
   GET `https://<your-app>.onrender.com/health` every 10 minutes.

## Environment variables (what the code actually reads)

| Variable | Required? | What it does |
|---|---|---|
| `PUKAAR_HOST` / `PUKAAR_PORT` | set by render.yaml | Bind address (0.0.0.0 in the cloud) |
| `PUKAAR_HMAC_KEY` | yes (public bind refuses without it) | Signs the provenance/audit trail |
| `PUKAAR_ADMIN_TOKEN` | strongly yes | Staff gate — control room asks for it at `/login`; without it every surface is public |
| `PUKAAR_DB` | recommended | SQLite path. Unset = in-memory (wiped every restart) |
| `ANTHROPIC_API_KEY` | for live AI | Presence auto-switches `PUKAAR_BACKEND=auto` from the free offline mock to live Claude |
| `PUKAAR_MODEL_INTAKE` | no (default `claude-haiku-4-5`) | Model that structures witness messages |
| `PUKAAR_MODEL_REASONING` | no (default `claude-sonnet-4-6`) | Set to `claude-haiku-4-5` for the all-Haiku cheapest setup |
| `PUKAAR_TELEGRAM_TOKEN` | optional | Free chat line (see below) |
| `WA_TOKEN`, `WA_PHONE_ID`, `WA_APP_SECRET`, `WA_VERIFY_TOKEN` | for WhatsApp | See [WHATSAPP-SETUP.md](./WHATSAPP-SETUP.md). The app refuses half-configured WhatsApp on purpose |
| `PUKAAR_SIM_AMBIENT=1` | optional | Busy self-playing showcase instead of the calm founder-driven board |

## What witnesses message

**Telegram — ₹0 and live in 5 minutes.** Message
[@BotFather](https://t.me/BotFather) → `/newbot` → copy the token → set
`PUKAAR_TELEGRAM_TOKEN` → redeploy. Witnesses message your bot
(`t.me/YourWaysideBot`); the bridge is already built in. No business
verification, no waiting. This is the fastest "real phone number" story
for a pilot demo.

**WhatsApp — the real thing, ~₹200 for a SIM.** Meta's Cloud API is free
for witness-initiated conversations at pilot scale; the webhook receiver
and sender are already built. Follow
[WHATSAPP-SETUP.md](./WHATSAPP-SETUP.md). Until Meta business
verification clears (days–2 weeks), the number runs in dev mode limited
to 5 test phones — start verification the day you get funded.

## What the AI costs (Claude Haiku 4.5)

Haiku 4.5 is $1 per million input tokens, $5 per million output. A full
witness report (3–5 short model calls) uses roughly 3k in + 700 out —
about **$0.006 ≈ ₹0.5 per case**. ₹500 of API credit covers ~1,000
witness reports. Everything else (demo, tests, CI) keeps running on the
free offline mock — the key is only ever read from the environment at
runtime.

**Key safety:** the key lives in the host's environment settings only.
Never commit it, never paste it in a file, and rotate it at
console.anthropic.com if it has ever appeared in a chat or screenshot.

## The full ₹10k picture

| Item | Cost |
|---|---|
| Hosting (Render free + pinger) | ₹0/mo |
| Chat line (Telegram) | ₹0 |
| WhatsApp SIM (when you go there) | ~₹200 once |
| Claude Haiku for ~1,000 reports | ~₹500 |
| Domain (optional — onrender.com URL works) | ~₹800/yr |
| **Left for aid kits (~₹430/person served)** | **~₹8,500 ≈ 20 people** |
