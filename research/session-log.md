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
- Layout: `pukaar/` = the working system (FastAPI, 184 tests, `make demo`).
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

## v1 direction (set by the founder, 2026-07-31)

After an NGO-director-perspective review, the founder set nine
priorities: English-perfect first · rider push notifications · cost
breakdown document · a flawless public website (high priority) ·
Google-quality map + real-road routing ("as close to Google Maps as
possible without the paid API") · rider side as a mobile-style app ·
a real WhatsApp number or equivalent chat line · kit depots optimised
across NGO locations · safety + tracking throughout.

The phased plan lives in **`research/product-plan.md`** (written for a
non-technical reader): 1 map-becomes-real, 2 rider mobile app +
notifications + safety, 3 kit depot network, 4 real chat line
(WhatsApp via Meta verification; Telegram as instant free equivalent),
5 website, 6 cost sheet.

**Founder decisions, answered (2026-08-01):** depots = placeholders for
now · Meta verification = not now, maybe later (so Phase 4 leads with
the Telegram/web-chat path) · domain = temp/free service for now ·
rider hardware = Android AND iPhone (PWA push must cover installed-PWA
iOS) · site byline = "Rustom Dubash, founder" confirmed.

**Phase 1 SHIPPED (2026-08-01):** the map became real. Built via a
three-way parallel workflow + serial integration:
- `pukaar/data/demo_zone.geojson` — 206-segment Nizamuddin-inspired
  named street network (Mathura Road, Lodhi Road, the dargah basti
  galis, Nizamuddin East block grid, rail corridor + station, Humayun's
  Tomb / Sunder Nursery parks, 7 landmarks). Representative geometry,
  NOT surveyed (sandbox blocks OSM); `tools/make_demo_zone.py`
  regenerates it byte-for-byte; `tools/fetch_real_roads.py` swaps in
  real OSM on the founder's machine. 13 validation tests incl. both
  connectivity invariants.
- `routing.py` v2 — RoadGraph over that geojson: walk/cycle/scooter
  speed profiles per road class, scooter banned from footways, A* on
  travel time, snap-to-nearest-legal-EDGE (mid-block entry, no
  teleporting to intersections). Old RoadMesh kept as fallback. 11
  tests.
- `static/basemap.js` — Google-style day + night MapLibre styles built
  from the same local geojson (white/amber roads, green parks, road
  names along lines, landmark labels) with self-hosted glyph PBFs
  under `static/vendor/glyphs/` (Klokantech Noto Sans Regular ranges,
  dir renamed to "Noto Sans Regular" — transparent to MapLibre).
- Integration: responders now have travel modes (Meena/Fatima walk,
  Arjun/Sunita cycle, Ravi/Imran scooter; MODE_SPEED_MPS), sim routes
  via RoadGraph, `/data/demo_zone.geojson` served by the API, all
  THREE map surfaces (control room `/`, `/supervisor`, `/witness`)
  ported Leaflet→MapLibre GL onto the new basemap, always-visible
  marker labels (mode glyph + name + live ETA), day/night
  `#theme-toggle` in the legend (localStorage-persisted), 90-day
  cells as a fill layer.
- **Bug caught live:** the basemap's geojson source is named "zone" and
  the overlay zone-ring reused the id, clobbering all streets — overlay
  sources renamed `zonering`. Playwright-verified all three pages, day
  + night, zero console errors; route lines visibly follow streets
  with turns and ETA labels ("Sunita · 6m"). 139 tests pass.

**Phases 2-6 SHIPPED (2026-08-01)** — "go with all phases":
- **Map, better** (the founder's "it doesn't work right"): cache-busting
  `?v=` params on every static include (stale-JS after `git pull` was the
  likely breakage — hard-refresh no longer needed), zoom/pan clamps +
  maxBounds so the camera can't get lost off-zone, 476 deterministic
  building footprints in the geojson + a zoom-faded building layer, round
  line joins. The basti now reads like a real quarter at z15+.
- **Phase 2 (rider app):** manifest.webmanifest + icons (amber pin, named
  Wayside) + sw.js → installable on Android and iOS (Add to Home Screen);
  real Web Push via pywebpush + self-generated VAPID keys stored in db
  (`/api/push/vapid`, `/api/push/subscribe`; offer pings pushed on
  wave_started; dead subs pruned) with an in-page Notification fallback
  when the tab is hidden; 🆘 SOS button (footer, on-duty only) → crit
  feed event + triple-beep; overdue safety alarm (enroute + stationary
  150 sim-s → once-per-order safety_alert; clock resets at accept — a
  stale-idle-clock false-positive was caught live and fixed).
- **Phase 3 (depots):** 3 placeholder depots (Basti Office, Nizamuddin
  East Community Room, Station-side Partner Shop) hold the stock
  (inventory.partner_id = depot id; network totals unchanged); dispatch
  routes the accepted rider via the cheapest-detour depot WITH stock
  (leg1+leg2 concatenated; ETA covers both); kit_pickup feed event at the
  depot waypoint; consumption + per-(depot,sku) courier restock (+8 at
  threshold 3); network stockout → direct route + coordinator flag; depot
  markers with live per-SKU stock tags on the map (amber when low);
  rider app shows "Collect the kit at X — detour already in your ETA."
- **Phase 4 (chat line):** telegram.py — full dormant adapter (long-poll
  bridge, inline-keyboard buttons, location/photo mapping, tg:<chat_id>
  as phone; 17 mocked tests; never constructed without
  PUKAAR_TELEGRAM_TOKEN, wired in __main__). Founder-facing setup doc:
  research/telegram-setup.md. WhatsApp path unchanged/dormant (Meta
  deferred by founder).
- **Phase 5 (website):** /site/index.html — self-contained Wayside page
  ("See it, send word."), zero external requests, responsive-verified at
  390/1440px, byline "Rustom Dubash, founder"; site/DEPLOY.md covers
  GitHub Pages + Netlify Drop free hosting.
- **Phase 6 (money page):** research/cost-breakdown.md — sourced,
  funder-readable; ~₹1.55L 8-week pilot incl. an explicitly-placeholder
  stipend line; "deliberately ₹0" section.
- Suite now at **167 tests, all passing**; every surface Playwright-
  verified again post-integration (0 console errors, 0 false safety
  alerts, 5 organic kit pickups in the seeded session).

**Iteration round (2026-08-02, "find issues and iterate"):** four real
defects found and fixed solo: (1) pywebpush missing from pyproject —
`make install` on the founder's Mac would silently disable real push AND
fail a test; now a dependency, plus package-data for the geojson/static.
(2) Service worker registered from /static/sw.js could only ever scope
/static/ — now served at /sw.js (root scope verified live:
`http://127.0.0.1:8877/`). (3) Deep-linked riders (?id=) never got a
notification-permission prompt (no user gesture) — first tap now
triggers it. (4) Depot pins were hand-guessed coords floating off-road
(East depot 212 m into empty canvas) — snapped onto the street graph at
boot; test updated to use snapped positions. Also probed routing for
silent straight-line fallbacks: 0 in 600 random routes across all three
modes. Doc counts refreshed (167 tests). All 167 pass; supervisor
re-verified live, zero console errors.

**Improvement loop (2026-08-03/04, standing order — running until told to stop):**
the founder asked for a self-pacing loop: research, find flaws, add
needed features, YC-level frontend, flawless routing, package/pricing
research. Log of each round: `research/loop-log.md`.
- **Round 1 (closed):** 20 confirmed defects fixed via finder-fleet +
  adversarial verification workflows — reserve-at-accept kit ledger,
  golden-run hijack guard, arrival-gated-on-pickup, PUKAAR_DB restart
  reconciliation, staff gate (PUKAAR_ADMIN_TOKEN + /login cookie),
  keyed coordinator render, scenario-button thread jump, pricing research
  (`research/pricing-research.md`, pilot ≈ ₹1,250/mo). 173 tests.
- **Round 2 (closed):** phones work now — the 539px grid-track bug
  (min-width:auto floor) and the viewport-locked shell (footer painting
  over panels) are fixed; all four surfaces measure exactly 390px on a
  390px phone. Plus /favicon.ico through the staff gate, send-button
  busy state on both phone panels, designed empty states for feed/cases,
  cache-buster → 20260804a. **175 tests.** Commit `5bb201b1d`.

- **Round 3 (closed):** the "burn it" round — 58-agent adversarial
  audit (12 finder dimensions, per-finding skeptics, 3.57M tokens)
  confirmed 45 findings; 30 fixed in one serial pass including both
  P1s (kit-ledger corruption across restarts; real-browser push dead on
  arrival from a pywebpush key-format mismatch). Features: offline
  rider PWA shell, mobile KPI chip strip, routing perf measured at 5×
  (0.5ms p50 — no optimization needed). research/kit-costs.md sourced.
  **184 tests.** Commits `583f96779` + `91bae8bdb`.
  ⚠ Awaiting founder word: PUKAAR→Wayside product-chrome rename
  (confirmed as the top UX finding; one word and I'll sweep it).

- **Round 4 (closed):** deferred-queue clearance — 72h case expiry
  enforced in retention (audit-logged, legacy tests rewritten to the new
  contract), provenance macs re-verifiable from stored rows (bool→0/1
  canonicalization), all 8 cross-thread dict iterations snapshotted,
  golden run stages clear of dedup cells + honest failure. **188
  tests.** Commit `7bdc8610a`.

- **Round 5 (closed):** pilot-readiness — witness page fully offline
  (SW shell + veil fix + honest no-signal toast, verified in airplane
  mode), CI now gates frontend JS syntax + 3.11/3.12 matrix, kit-economy
  invariants proven under forced stockout (120 reports vs 57 kits),
  #case-XXXX deep links. **189 tests.** Commit `cd50c5445`.

- **Round 6 (closed):** three builder agents in parallel — rider
  turn-by-turn street directions (nav-app UI, verified via live accept),
  witness queued-send (offline reports auto-flush on reconnect, E2E
  verified), site refresh with true R3-R5 proof points. Cache reconciled
  to 20260804f after a builder-side partial bump that would have broken
  offline. Loop heartbeat moved server-side (send_later Routine) after
  in-session wakeups kept getting superseded. **194 tests.** Commits
  `28e8b5883` + `20bf7c971` + `35ddfc2bf`.

- **Round 7 (closed, founder-directed):** the five calls — Wayside
  rename everywhere (internals untouched), Goonj claim removed + deck
  rebuilt, Telegram parked (/witness is the demo line), private demo
  tour artifact published, 3-minute demo script written
  (research/demo-script.md). **194 tests.** Commit `f0bd6dc7c`.

- **Round 8 (closed):** coordinator supply strip (dry SKUs + courier
  countdowns), then a 16-agent sweep of rounds 5-7 code confirmed 11/11
  findings, all fixed: honest offline taps in the rider app (false
  "arrived" success killed), thread-pinned + idempotent witness outbox,
  offline-boot map, turn-by-turn XSS/overflow, Devanagari rename
  stragglers (पुकार→वेसाइड). **196 tests.** Commits `4be60fbed` +
  `a9cbb86bf`.

- **Round 9 (closed):** real witness photo upload — multipart endpoint
  (3 MB, image-only, flood-capped), staff-gated viewing in the case
  detail, retention deletes the bytes from disk, and pre-case photos
  retro-link when the pin completes the case (gap caught by live E2E).
  Offline uploads honestly refused. **200 tests.** Commit `7e53f9ee6`.

- **Round 10 (closed):** demo recorder rebuilt (coordinate-based clicks
  beat 1 Hz keyed re-renders; captions de-GoodSAM'd, counts honest,
  Wayside close) and **docs/wayside-demo.webm** recorded (~3.5 min),
  delivered to the founder, committed. Commits `d5c8a332d`/`bd0b58c0f`.

- **Round 11 (closed):** shift-handover report (svc.shift_summary →
  printable /shift + JSON /api/shift, window-scoped, staff-gated, live
  verified + screenshotted) and research/deploy-app.md (founder's
  Fly.io/Render private-URL checklist; Dockerfile documents
  PUKAAR_MEDIA_DIR volume). **202 tests.** Commit `5488d2e0e`.

- **Round 12 (closed):** bilingual rider app (Devanagari on every
  action label, verified live) + a security sweep of the round-9/11 photo
  & shift code — 9/10 findings fixed including a P1 unauthenticated
  upload DoS (body-limit middleware + chunked read, verified 413),
  orphaned-file leaks (unlink + retention backstop sweep), shift
  undercount (durable outcomes not the 250-feed), photo idempotency.
  **206 tests.** Commits `b4707f658` + `04be2bcbb`.

- **Round 13 (closed):** accessibility + i18n — lang="hi" on every
  Devanagari string (rider labels, banner, duty pill, chat bubbles in
  both witness + control room), role="status" on the witness toast;
  verified live (10 tagged / 0 untagged, all interactive elements named).
  Skipped the CI-pages item (repo is an is-a.dev fork; auto-deploy would
  collide). **206 tests.** Commit `9f5117c41`.

- **Round 14 (closed):** first broad audit since R3 — 12/12 findings
  fixed, incl. a P1 that broke the documented token deploy (witness page
  + assets were 401-gated; fixed with scoped public /api/witness/state +
  opened static/data, staff surfaces stay gated; verified live). Plus
  webhook-inert-without-secret, chunked body-limit bypass, responder
  api() await, name-escaping, orphan-sweep grace, 2 more thread snapshots.
  **208 tests.** Commit `6b9cfecd7`.

- **Round 15 (closed):** responder roster/vetting panel (coordinator
  side — vetting badges, medical marker, served count, on/off-duty toggle
  that dispatch respects; svc.roster()/set_active + /api/roster/active,
  keyed render, verified live) + per-mode connectivity check in the
  fetch_real_roads OSM importer. **211 tests.** Commit `7198fdf8c`.

---
**Last updated:** 2026-08-05, after loop Round 15. Before that: the
find-issues iteration of 2026-08-02. Before
that: routing/ETA engine and the witness/supervisor interface split —
all 111 tests pass; verified live with Playwright (route lines render
as real bent paths, ETA shows correctly, all 4 pages load with zero
console errors, a real message typed on /witness flows through to a
real case in the backend).
