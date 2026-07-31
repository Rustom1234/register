# Wayside — session log / handoff

Running log of what's been built and decided, kept so work can resume
cleanly on a new machine or in a fresh session. Updated roughly every 5
responses — check the "Last updated" line at the bottom.

## What this is

A witness-powered street-aid system, originally built for the Kevin Xu
Innovation Challenge (Equitech alumni track). One WhatsApp number lets
anyone who stops on the street report a person who needs help; a
deterministic 112 gate catches real emergencies first; an AI agent
structures the report into a location + need + urgency; a GoodSAM-style
parallel dispatch offers the case to nearby NGO responders, first-accept
wins; outcomes are recorded and the witness is told how it ended.
No cameras, no database of the people served.

## Repo / branch / hard rules

- Repo: `Rustom1234/register` (a fork of is-a-dev/register, repurposed)
- Branch: `claude/street-aid-research-4xqdpu` — all work happens here
- **Hard rule (CLAUDE.md): never use a paid Anthropic API key for anything
  in this repo — coding, testing, demos, screenshots, video. Everything
  runs on `PUKAAR_BACKEND=mock` (the default). CI must stay key-free.**
- Layout: `pukaar/` = the working system (FastAPI, 111 tests, `make demo`).
  `research/` = findings, plans, the KXIC proposal, and (`research/pitch/`)
  the pitch deck.

## Naming: Pukaar → Wayside

The project's working name was "Pukaar" (Hindi, "the call"). After a
multi-round brainstorm (English-only per the user's request, surveyed
against comparable products — StreetLink, GoodSAM, PulsePoint, Samaritan,
Robin Hood Army, Goonj, etc.) the user picked **Wayside**, tagline
**"see it, send word."**

**Renamed so far: the pitch deck and the long-form web pitch only.**
**Not yet renamed: the actual running product.** `pukaar/` — code, UI
strings (control room, responder app, phone mock), tests, docs, and
`research/kevin-xu-proposal.md` — all still say "Pukaar." A full rename
sweep has been offered repeatedly and is a known, scoped next step, not
done because the user hasn't said the word yet.

## What's built and working (`pukaar/`)

- FastAPI + SQLite backend, 111 automated tests, `MockBackend` regex NLU
  (no API key needed; Claude backend exists in `backends.py` but stays
  dormant per the hard rule)
- Trilingual (English/Hinglish/Devanagari) WhatsApp-style intake, with a
  deterministic 112 emergency gate that outranks everything else
- Kit ordering (medical/food/shelter) with code-enforced caution
- GoodSAM-style dispatch: parallel offer waves, first-accept via CAS,
  overnight requeue, coordinator escalation for pinless/ambiguous cases
- Privacy/retention: closed-case-only data, media purged 72h, exact
  lat/lng nulled 7 days post-close, 90-day aggregate heat-cells only,
  HMAC provenance tagging
- Resilience hardening: conversation persistence across restarts, per-witness
  rate limiting, Meta webhook signature verification, non-local bind
  refuses without an HMAC key, `/health` watchdog
- Frontend: redesigned control room (dark ops theme, design tokens, marker
  glide animation, WhatsApp-style phone mock, category-coded map), a
  standalone responder phone app, a coordinator queue, a metrics/kill-criteria
  dashboard, a printable session report, an interactive session replay
- A MapLibre GL experiment lives in a **separate worktree/branch**
  (`claude/maplibre-gl-experiment` at `/home/user/register-maplibre`) —
  Google Maps-like street basemap with an offline fallback, built so the
  main branch is never put at risk. Merge decision is pending the user
  testing it locally.
- **Real road-following responder movement + ETA** (`pukaar/routing.py`,
  new): responders used to glide in a straight line toward a case,
  cutting across roads/buildings. There's no reachable live routing API
  from this sandbox (Overpass/OSM is blocked by the network policy — see
  below), so this generates a deterministic, locally-coherent street mesh
  around the demo zone (rotated + jittered grid, ~625 nodes, connectivity
  guaranteed) and does real Dijkstra pathfinding over it — genuine
  multi-waypoint routes and realistic detour distances (1.4–1.9x
  beeline), not surveyed Nizamuddin geometry. Wired into `sim.py`'s
  `_responders_move`; exposed via `/api/state` as `route` (waypoints) and
  `eta_s`/`dist_m` per responder; drawn as a real bent polyline on the
  map (was a straight dashed line) with an ETA readout on the marker
  tooltip, the sidebar responder card, and the standalone responder app.
- **Three separate interfaces**, per the user's request that a demo
  showing one combined screen isn't realistic:
  - `/witness` (new) — standalone reporter view: just the phone chat +
    a map for pin-dropping + scenario buttons. No supervisor/responder
    controls visible. Verified end-to-end (typed Hinglish message → real
    bot reply → pin drop → real case created in the backend).
  - `/supervisor` (new) — standalone map + live feed + coordinator queue
    + open cases, with quick links to the other two. Reuses `app.js`
    (now defensive about missing phone/responder-panel DOM via
    `wirePhone()`/`wireRespPanel()` guards) rather than forking it.
  - `/responder` — already existed, unchanged.
  - `/` — the original all-in-one demo/recording harness, left as-is
    (still useful for pitch videos where one screen needs to show
    everything at once).

**Network policy note for future sessions:** this sandbox's egress proxy
denies `overpass-api.de` (and presumably other live map/routing APIs) —
confirmed via `curl $HTTPS_PROXY/__agentproxy/status`, reason
`policy denial`. Don't re-attempt live OSM fetches; the synthetic-mesh
approach above is the worked-around answer already in the repo.

## Pitch deliverables (`research/pitch/`)

- `wayside-kxic-pitch.pptx` — 13 slides, dark theme throughout, matches the
  depth of the long-form web pitch (not the older 9-slide terser version).
  Regenerate with `npm install && node build_deck.js` from that folder.
- `wayside-kxic-pitch.md` — the same pitch as plain text, kept in sync with
  the pptx's slide order
- `assets/` — 6 screenshots (control room, witness phone, responder offer,
  on-arrival checklist, coordinator view, kill-criteria dashboard), header
  chrome cropped out of each
- A long-form illustrated **web pitch** (single self-contained HTML file,
  fonts and images embedded) — published at
  **https://claude.ai/code/artifact/ae815c70-4e6e-4d80-a6c5-d550153a7b86**.
  ⚠️ **Its source only exists in this container's `/tmp` scratchpad, which
  does not transfer to a new machine.** The published link itself should
  keep working (Artifacts are hosted separately), but if you want to edit
  it again after switching machines, it will need to be rebuilt from
  scratch (same content is mirrored in `wayside-kxic-pitch.md` above, so
  nothing is lost, just the exact HTML/CSS build).

## Claims flagged for your confirmation (not mine to decide)

- **"Rustom Dubash"** as the presenter name on the deck/close slide —
  inferred from your email address, never explicitly confirmed by you
- **"an existing Goonj relationship"** — factual claim on the Customer
  slide about a real organization; I can't verify it's true, only that it
  reads fine
- **The GoodSAM dispatch-speed line** — currently still reads *"GoodSAM
  showed that offering a case to several nearby responders at once,
  first-to-accept, gets a yes inside a minute"* in every shipped
  deliverable (pptx, .md, web pitch), unchanged, because you asked me to
  keep the fix chat-only for now. That phrasing isn't backed by a public
  stat I could find. The defensible replacement, sourced to a 2025
  *Resuscitation* study on GoodSAM-*pattern* (not GoodSAM-branded) systems
  (median turnout time 1:42–2:22, not arrival time):
  > GoodSAM-style dispatch offers a case to several nearby responders at
  > once, first-to-accept — and gets someone moving in under two minutes.
  Full citations for this and for StreetLink/DIGIPIN are in the
  conversation; not yet re-applied anywhere on your instruction.

## Standing constraints from this session

- **Solo/lean work only** — no multi-agent fleets unless explicitly
  requested; you shut down an agent-fleet round hard earlier ("STOP …
  dont run so many agents for no reason")
- **Never use API keys**, ever, for anything in this repo
- Be mindful of subscription usage — it's been reported at 100% weekly
  before

## Known open code leads (not fixed — deliberately left alone to stay lean)

- A responder switched to manual control can hold a simulated order frozen
  "onsite" indefinitely, because all-manual mode disables the simulator's
  auto-close — blocks new offers from rendering for that responder until
  worked around by picking a different one
- `responder.js`'s `poll()` catches render exceptions the same way it
  catches fetch/network exceptions, which can hide real bugs

## How to pick this back up

1. `git clone` (or pull) `Rustom1234/register`, checkout
   `claude/street-aid-research-4xqdpu`
2. Read `research/README.md` and `research/pitch/README.md` for orientation
3. `cd pukaar && make demo` to run the working system locally
   (`PUKAAR_BACKEND=mock` is the default — no key needed)
4. This file (`research/session-log.md`) for what's done / open / flagged
5. GitHub link: https://github.com/Rustom1234/register/tree/claude/street-aid-research-4xqdpu

---
**Last updated:** 2026-07-31, after the routing/ETA engine and the
witness/supervisor interface split. All 111 tests pass; verified live
with Playwright (route lines render as real bent paths, ETA shows
correctly, all 4 pages load with zero console errors, a real message
typed on /witness flows through to a real case in the backend).
