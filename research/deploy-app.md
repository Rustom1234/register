# Putting the Wayside app on a private URL

This is the live **app** (control room + witness + responder), not the
marketing site — see `site/DEPLOY.md` for that. The goal: a link you can
hand a judge where the control room sits behind a login and the witness
page is open, on a URL that's yours and costs a few dollars a month.

Everything here is founder-runnable. No API key is needed — the app runs
on its built-in mock agent unless *you* choose to add one.

---

## What "private" means here

- **Control room, supervisor, exports, live chats** → behind a staff
  token. A visitor without the token gets a 401.
- **Witness reporting page + webhooks** → open (a member of the public
  can't log in to report). This is by design.
- You share the URL **plus the token** with people you trust; you share
  the URL **alone** for someone to only try the witness side.

The token is one value you invent (any long random string). Treat it
like a password.

---

## The four settings every hosted deploy needs

| Variable | Why it matters | Example |
|---|---|---|
| `PUKAAR_ADMIN_TOKEN` | The staff gate. Without it, **everything is public.** | a 32-char random string |
| `PUKAAR_HMAC_KEY` | Signs the provenance trail; the app **refuses to boot** on a public bind without it. | another random string |
| `PUKAAR_DB` | SQLite path **on a mounted volume** — without it all cases die on every redeploy. | `/data/pukaar.db` |
| `PUKAAR_MEDIA_DIR` | Uploaded witness photos — same volume, or they vanish and `/api/media` 404s. | `/data/media` |

Optional: `PUKAAR_SEED_DEMO=1` gives a lively pre-seeded demo session
(recommended for judges). HTTPS is required for the responder app's
install + push — every platform below terminates TLS for you.

Generate the two secrets once, on your Mac:
```bash
python3 -c "import secrets; print('ADMIN', secrets.token_urlsafe(24)); print('HMAC ', secrets.token_urlsafe(24))"
```
Keep both somewhere safe.

---

## Fastest path — Fly.io (Mumbai region, ~$3–6/month)

Fly runs the Docker image we already ship, close to Delhi, with a
mounted volume for the database and photos.

**One-time setup**
```bash
# 1. Install flyctl and sign in (a card is required; the machine is tiny)
curl -L https://fly.io/install.sh | sh
fly auth signup            # or: fly auth login

# 2. From the repo root, in the pukaar/ folder:
cd pukaar
fly launch --no-deploy --name wayside-<yourname> --region bom
#   - "copy existing Dockerfile?"  YES
#   - "deploy now?"                NO  (we set secrets + volume first)

# 3. Persistent volume for the DB + photos (1 GB is plenty)
fly volumes create wayside_data --region bom --size 1

# 4. The secrets (paste the two you generated above)
fly secrets set \
  PUKAAR_ADMIN_TOKEN='<your-admin-token>' \
  PUKAAR_HMAC_KEY='<your-hmac-key>' \
  PUKAAR_DB=/data/pukaar.db \
  PUKAAR_MEDIA_DIR=/data/media \
  PUKAAR_SEED_DEMO=1
```

**Mount the volume** — add this to the generated `fly.toml`:
```toml
[[mounts]]
  source = "wayside_data"
  destination = "/data"

[http_service]
  internal_port = 8877
  force_https = true
  auto_stop_machines = true     # scales to zero when idle — cheaper
  min_machines_running = 0
```

**Deploy**
```bash
fly deploy
fly open                        # opens https://wayside-<yourname>.fly.dev
```

**Hand it out**
- Judges (full access): `https://wayside-<yourname>.fly.dev/login?token=<your-admin-token>`
  — one click sets their cookie, then every page just works for 30 days.
- Witness-only (open): `https://wayside-<yourname>.fly.dev/witness`

**Check it's healthy**
```bash
fly logs                        # should show "Wayside demo · backend=mock"
curl https://wayside-<yourname>.fly.dev/health   # {"ok": true, ...}
```

---

## Even simpler, if you don't want a card on file

- **Render.com** — connect the GitHub repo, "New → Web Service", it
  detects the Dockerfile. Add the same four env vars in the dashboard,
  attach a disk mounted at `/data`. Free tier sleeps after inactivity
  (fine for a demo you wake before showing); paid is ~$7/mo always-on.
- **Railway.app** — same idea, `$5` starter credit, add a volume at
  `/data` and the four vars.

Both give an `https://…` URL automatically. The env vars and the `/data`
mount are identical to the Fly steps above.

---

## Before you show it to anyone (2-minute check)

1. Open the bare URL in a private window → the control room should
   **refuse** you (401). Good — the gate works.
2. Open `…/login?token=<token>` → you're in.
3. Open `…/witness` in the private window → it works with no token.
4. `…/health` returns `{"ok": true}`.
5. If you set `PUKAAR_SEED_DEMO=1`, the map is already busy with riders.

If step 1 lets you in without the token, `PUKAAR_ADMIN_TOKEN` didn't
take — re-check `fly secrets list` and redeploy.

---

## Turning it off / costs

- Fly scales to zero when idle with the config above, so a demo machine
  costs roughly a dollar or two a month; delete it with
  `fly apps destroy wayside-<yourname>` when the challenge is over.
- Nothing here bills for AI: the app is on the mock agent. If you ever
  set `ANTHROPIC_API_KEY`, that's the deploying org's own key and
  funding — never part of the demo.
