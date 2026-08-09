# ⭐ Overnight summary for the founder (read this first)

**Pull first:** `git pull` → you want commit `35139f34c` or later.
Then `cd pukaar && .venv/bin/python -m pytest -q` → **224 passed** means
you're on tonight's build. Boot with NO flags — the calm board is the
pitch mode. Full walkthrough + final checklist: `research/demo-script.md`.

**What happened tonight (12 rounds, all pushed):** your five persona
critics (competition judge, product skeptic, NGO operations director,
skeptical CTO, mobile field reviewer) audited the product; every P0/P1
and nearly every P2 they found was verified live and fixed:

- **Safety:** the 112 gate now catches heart attack, stroke, drowning,
  choking, childbirth, suicide and "cannot breathe" — and no longer
  bounces ordinary Hindi wound reports ("pair se khoon beh raha hai")
  away with nothing filed; bounces are counted on the shift handover.
- **Nobody gets lost:** a witness whose landmark isn't understood is
  filed as a landmark-only case for your request-pin rail instead of
  being asked "where?" forever; a food report near a medical case stays
  a separate case; STOP now truly deletes the thread.
- **Coordinator rails:** hand-offs are consent offers (the rider still
  taps), stuck jobs release-and-re-wave honestly instead of being closed
  with a lie, night holds are visible, stock is staff-adjustable, and
  vetting actually gates dispatch.
- **The demo feels right:** the golden button self-arms on a cold board,
  travel time auto-compresses (⏩) and hands your speed back, riders hug
  streets to sub-pixel accuracy at 30x, offer cards carry the witness's
  words + road-true metres + honest countdowns, declines/assigns/pauses
  all speak instead of failing silently.
- **Phone-ready:** outcome buttons sticky above the fold, AA contrast
  for sunlight, composer on the first screen, offline sends shown as
  honest pending bubbles, 44px touch targets.
- **Paper trail:** one test count (224) across deck/README/proposal/
  artifacts; the demo-tour and guide artifacts rebuilt on the current
  product; the deck's rename caveat replaced with the provenance story.

**Links:** guide (pitch script + feature map):
claude.ai/code/artifact/630a49b0-fe6d-406c-8561-a4b7179ccd6c · tour
(shareable six-frame walkthrough):
claude.ai/code/artifact/5ab77ba7-51bd-4da7-ac11-1eb3c46c82c3

Round-by-round detail below.

---

# Wayside improvement loop — round log

Self-paced loop started 2026-08-02 on the founder's instruction: research,
find flaws, needed features, integration-readiness, YC-level frontend,
fast/flawless routing, packages + estimated prices. Runs until told to stop.
One entry per round; newest first.

## Round 1 — adversarial review + pricing research (CLOSED 2026-08-04)

25-agent fleet: 4 read-only finders → per-finding adversarial verifiers →
20 findings CONFIRMED, 0 rejected. Fixed this round (serially, then
regression-pinned in `tests/test_loop_r1.py`, 173 tests green):

- **Kit ledger rebuilt as reserve-at-accept:** stock leaves the depot the
  moment a rider accepts (kills the two-riders-one-last-kit race), returns
  on not_found/declined (`settle_kit`, shared by sim close AND the human
  close path — which previously never touched inventory at all).
- **Golden run can no longer hijack a busy rider** (idle+non-manual
  medical required; declines degrade to needs_coordinator) and
  `_sync_states` now recovers 'onsite' orders too — the stranded-order
  class is closed.
- **No arriving without the kit:** arrival is gated on pickup, so a route
  that passes the case before the depot keeps driving.
- **PUKAAR_DB restarts reconcile:** sim clock persists and resumes
  (retention/dedup windows stay monotonic), escalation timers re-arm from
  the DB, depot stock is no longer silently re-seeded.
- **Staff gate for hosted deploys:** PUKAAR_ADMIN_TOKEN + /login cookie
  protects every surface/API except witness webhooks + /health; Dockerfile
  no longer bakes PUKAAR_ALLOW_INSECURE=1; boot refuses WhatsApp-live
  without WA_APP_SECRET; Telegram token validated loudly at boot (getMe).
- **Frontend:** case-click pan had lat/lng swapped (MapLibre order);
  coordinator assign-dropdown no longer resets every second (keyed
  render); supervisor collapses to one column on phones; scenario buttons
  now jump the phone panel to the spawned thread on / AND /witness (was a
  dead end there); kits tile says "across 3 depots" not "partner_1";
  kit returns show in the feed.
- **Deferred (logged, low):** feed/conversations thread-safety (GIL +
  copies make it benign today); no-movement alarm unreachable for
  sim-moved manual riders (SOS covers humans); supervisor mobile still
  slightly overflows horizontally (~511px track at 390px) — next round.

Pricing research landed: `research/pricing-research.md` (sourced Aug-2026
numbers). Headline: realistic pilot run-rate ≈ **₹1,250/mo** (Meta
utility ₹0.115/msg + free service conversations; Fly.io Mumbai $3-6;
Sarvam STT ₹0.50/min; Haiku ~₹0.30-0.85/report) — comfortably under the
cost doc's ₹3-4k; no researched line came out above the doc.

---

## Round 2 — CLOSED (2026-08-04)

**Theme: the product finally works on a phone.** Round 1 deferred the
supervisor's mobile overflow; this round root-caused and killed the whole
class, then shipped the small YC-polish items that make the surfaces feel
finished.

### Root cause found (the interesting one)
At 390px the control room and supervisor rendered at **539px wide** — not
a padding bug but a grid-sizing one, found live with Playwright probes:

1. `#left`/`#right` are grid items with default `min-width: auto`; the
   ≤1100px media rule flips them to `overflow: visible`, so their
   min-content (the widest feed line, 517px) became a hard **floor for
   the 1fr track**. `#center` always had `min-width: 0` — its siblings
   never got it. One line each fixed it.
2. `html, body { height: 100% }` + `overflow: hidden` kept the shell
   viewport-locked after panels stack, so the grid rows overflowed
   `#layout` and the **footer painted over the feed**. Mobile now gets
   `height: auto; min-height: 100%` and a natural page scroll.
3. The topbar itself (596px of tools) never wrapped: `#topbar`,
   `.top-right`, `.top-tools`, `.legend`, `#foot` all wrap ≤900px;
   `.brand-sub` hides ≤620px.

**Verified: all four surfaces measure exactly 390px at 390×844 and
1600px at 1600×1000, zero 4xx, zero page errors.** Screenshots eyeballed —
wrapped topbar reads as designed, footer overlap gone.

### YC polish shipped
- **/favicon.ico route** (open through the staff gate — browsers request
  it on the bare /login page too). Icon `<link>`s added to all four HTML
  pages. No more per-page-load 404 noise.
- **Send-button busy state** on both phone panels (app.js + witness.js):
  disabled while the POST is in flight, `sendBusy` guard for Enter-mash,
  `finally` re-enable so a failed fetch can't wedge the button.
  `.send:disabled` dims at 45%.
- **Empty states**: feed shows "Quiet so far — dispatch events stream
  here the moment a report lands."; cases panel upgraded to the same
  designed `.empty-note` ("No open cases — quiet streets 🌙").
- **Cache-buster bumped** `20260801a → 20260804a` on all static includes.

### Verification
- Playwright live suite (scratchpad/verify_r2.js): overflow sweep on all
  4 surfaces × 2 viewports; empty-state render exercised through the real
  `renderFeed`/`renderCases` path; send button observed disabled
  mid-flight through a 600ms-delayed route and re-enabled after; favicon
  200 image/png without a staff cookie.
- New `tests/test_loop_r2.py` (favicon PNG magic bytes + open-through-gate
  with `PUKAAR_ADMIN_TOKEN` set). **Suite: 175 passed.**
- Commit `5bb201b1d` pushed.

### Deferred / next-round candidates
- Mobile map tiles strip eats ~40% of the 430px map — consider a
  collapsed single-row tile mode ≤620px.
- Feed/conversations thread-safety hardening (carried, still benign).
- Routing perf re-measure at 5× fleet (carried).
- Rider PWA offline shell (sw.js currently network-first passthrough).

---

## Round 3 — CLOSED (2026-08-04)

**Theme: full-scale burn.** The founder said "burn it" — so this round ran
a 58-agent workflow (12 read-only finder dimensions × adversarial
per-finding verifiers × a kit-cost researcher; 3.57M subagent tokens,
765 tool calls, ~2h) while the main session built features in parallel,
then landed every actionable confirmed finding serially.

### Features (shipped mid-audit, commit 583f96779)
- **Offline rider shell**: responder PWA precaches its app shell in a
  versioned cache; verified by killing the network in Playwright and
  reloading — the app renders from cache. Navigations stay
  network-first; /api/* never cached; install survives partial precache.
- **Mobile KPI chip strip**: supervisor tiles collapse to one 39px
  swipeable row under 620px (was a 177px stack over the map). Cascade
  lesson: the rule must sit AFTER the ≤1100px block — same specificity,
  file order decides.
- **Routing perf at 5× fleet, measured**: p50 0.5ms/route, worst 1.6ms,
  snap 205µs (1000-route benchmark per mode). 30 riders re-planning
  every second ≈ 1.5% of one core — the O(edges) snap needs no spatial
  index at pilot scale. Deferred item closed with data.

### Audit results (commit 91bae8bdb)
Fleet claimed 46 findings; adversarial verification confirmed 45
(P1 4 / P2 20 / P3 21). Landed: both code P1s, all actionable P2s, and
11 of the P3s. Standouts:
- **P1 ledger corruption**: kit reservations were process-memory while
  their stock decrements were durable — a PUKAAR_DB restart
  mid-delivery double-consumed at re-attach and orphaned the return.
  The ledger (+ owed courier restocks) now persists in push_meta beside
  the sim clock; regression test restarts a Sim over the same Store.
- **P1 push never delivered**: pywebpush 2.3's string path can't parse
  a PEM (`Vapid.from_string` expects raw base64) — every real-browser
  send would have died. Verifier proved it empirically in the venv. Now
  we pass the Vapid object, send with ttl=300, log rejections, prune
  after 5 strikes (404/410 immediately).
- **CAS close**: sim auto-close vs human close raced check-then-act and
  could double-write outcomes; both paths now claim the row with a
  conditional UPDATE (db.Store.claim existed for exactly this).
- **Recheck leak**: witness "No" on a recheck cancelled accepted orders
  without settling the kit — stock permanently short. service→sim hook
  settles it; _sync_states got a safety rail for unsettled external
  closes.
- **Flood cap**: /api/wa/inbound's per-phone budget was bypassable by
  minting a phone per request; global 30/10s window (emergency texts
  exempt) + phone-shape and finite-coordinate validation.
- **Keyed frontend renders**: the 1 Hz innerHTML rebuild destroyed open
  dropdowns and ate clicks; resp-select/conv-select/cards/quick now
  render keyed with in-place volatile text — node identity verified
  stable across 3 live polls.
- 25 more (telegram at-least-once + probe(), health trim, Secure
  cookie, VAPID-rotation reconcile, SW static freshness, witness
  proto-key, marker-click pin teleport, follow-cam gestures,
  AudioContext resume, AA contrast, 44px targets, witness map-first,
  docs drift…) — full list in the commit message.

### Not fixed on purpose
- **PUKAAR vs Wayside product chrome** (a confirmed P1 by the UX
  dimension): every surface still says PUKAAR while the deck, site, and
  PWA identity say Wayside. Renaming the product is the FOUNDER's call —
  flagged, not acted on. One word and the sweep happens.
- Provenance HMAC type normalization (signature-compat migration
  needed), expires_at pin scrub, feed/conversations thread-safety,
  golden-run dedup-merge edge — deferred with reasons, queued for R4.

### Research
- `research/kit-costs.md`: itemized, source-linked Delhi prices
  (accessed 2026-08-04) for all three kits — MED ≈₹307 retail/₹172
  wholesale, FOOD ≈₹69/₹50, SEAS ≈₹371/₹173; one-time 3-depot seeding
  ≈₹6,891; year-1 stock ≈₹36,500 incl. 15% contingency. Cross-linked
  from cost-breakdown.md.

### Verification
Suite 175 → **184** (9 new pins: restart ledger ×2, recheck settle, CAS,
escalated settle, dedupe window/closed-case, inbound validation+flood,
health trim, push lifecycle). Full Playwright re-verify: overflow clean
at 390/1600 on all four surfaces, tile strip 39px, offline shell serves
under airplane mode with cache `wayside-20260804c`, witness mobile is
map-first, keyed dropdowns survive polls. Buster → 20260804c.

---

## Round 4 — CLOSED (2026-08-04)

**Theme: clear the deferred queue.** The four audit findings parked in
Round 3, landed and pinned:

1. **72h case contract enforced** (was P3-4): `expires_at` was written,
   never read. `purge()` now closes non-escalated cases past contract
   (audit-logged), releases dangling orders, and the existing clocks
   (pin 7d, aggregate 90d) take over. Rewrote two legacy tests whose
   premise ("open case at 90 days keeps its pin") the new contract makes
   impossible by construction.
2. **Provenance re-verifiability** (P3-3): sign() canonicalizes bools to
   the stored 0/1 before hashing — an auditor holding only the DB can
   now re-verify every order mac. Pinned: bool/int sign identically,
   stored row re-verifies, distinct ints stay distinct.
3. **Thread-safe iteration** (P3-2): all 8 shared-dict iteration sites
   snapshot with list() — sim thread vs API-worker RuntimeError class
   closed for conversations, pending escalations, pending restocks, and
   the report renderer.
4. **Golden-run honesty** (P3-1): stages its pin clear of open dedup
   cells via the same query the service merges with; when a merge still
   swallows the report it says so instead of claiming success.

Suite **188** (4 new pins). Live sanity: all 4 surfaces load clean.
Commit `7bdc8610a`.

**Still open by choice:** PUKAAR→Wayside chrome rename (founder's word
pending — one message and it happens); manual-rider movement semantics
(SOS covers humans; logged as design note, not a defect).

**R5 candidates:** witness-page offline behavior (SW covers /responder
only), supervisor case-detail deep links, a night-theme pass on the
witness map, load test at 10× report volume, CI workflow file
(pytest on push — suite is fully offline by design).

---

## Round 5 — CLOSED (2026-08-04)

**Theme: pilot-readiness — offline, CI, proof under pressure.**

1. **Witness page works offline.** The root SW precaches the witness
   shell (page, JS, CSS, vendored MapLibre, basemap, street geojson) and
   witness.js registers it. Verification caught a real bug in my own
   feature: the "connecting…" boot veil only lifted on a successful
   poll, so the offline shell rendered but was UNTOUCHABLE. It now lifts
   on the failed first poll, inputs wire, and a failed send/scenario
   shows an honest "⚠ No signal" toast. Verified end-to-end in
   Playwright airplane mode (screenshot r5_witness_offline.png).
2. **CI gates the frontend.** pukaar-tests.yml adds `node --check` over
   all static JS (this exact gate caught real breakage twice this
   session), a Python 3.11 + 3.12 matrix, and the key-free rule inline.
3. **Kit economy proven at stockout.** New load test: 120 reports vs 57
   seeded kits forces the depots dry, then asserts the exact invariants
   round 3's audit found leaking — stock ≥ 0 everywhere, reservations
   map only to live accepted/onsite orders, no offered-order black
   holes, dispatch keeps closing. (The existing 300-case tick-budget
   test already covered throughput; this one covers correctness under
   scarcity.)
4. **Case deep links.** /supervisor#case-8512 opens that case's panel
   and pans the map; opening writes the hash, closing clears it. A
   coordinator can now paste a case link in any chat.

Suite **189** (commit message says 190 — mea culpa, off by one).
Cache/buster 20260804e. Commit `cd50c5445`.

**R6 candidates:** night-theme witness map (deliberate day-theme choice —
revisit only if founder wants), rider-side turn-by-turn text directions,
witness queued-send (retry the failed report automatically when signal
returns), depot restock notification via push, site/ pitch page refresh
with the R3-R5 features (offline + kit costs are demo-worthy).

---

## Round 6 — CLOSED (2026-08-04)

**Theme: parallel build — three agents, three features, one integration.**
(Also fixed the loop's own cadence: in-session wakeups kept getting
superseded, so the heartbeat now lives server-side via a scheduled
message that fires into the session as a real turn.)

1. **Rider turn-by-turn directions** (commit `35ddfc2bf`): the road
   graph's street names flow through A* (`route_named`, 3-tuple `route()`
   contract preserved + pinned), sim collapses legs into ≤8 honest steps
   ("Musafir Khana Road · 68 m", "gali" for unnamed lanes), clears on
   every close path, and the responder app renders them nav-app style —
   done legs dimmed, current leg glowing. Verified by accepting a live
   offer in Playwright as Meena: 4 steps, real names, highlight moves.
2. **Witness queued-send** (`28e8b5883`): a report that fails offline
   queues in localStorage (cap 10, text/location/photo/voice only —
   never stale button replies) and auto-flushes in order on the 'online'
   event, on the first healthy poll, or on page load. Verified E2E:
   offline send → "saved, will send by itself" → reconnect → green
   "✓ 1 saved message sent." → message confirmed in the backend thread.
   No report a witness types is ever lost.
3. **Site refresh** (`20bf7c971`): the public page now carries the true
   proof points — offline apps, 189→194 tests, restart-safe ledger,
   half-a-millisecond routing, itemized kit costs (₹172/₹50/₹173,
   ₹36,500 year-one) — and FIXES an old overclaim (pins delete "on
   schedule", not "the moment a case closes").

Integration caught one real hazard: the turn-by-turn builder bumped only
responder.html's cache-buster, which would have broken BOTH offline
shells (SW precaches exact URLs). Reconciled everything to 20260804f and
re-verified airplane-mode on both apps. A container restart mid-verify
also cost a server reboot — and exposed that my verify script fetched
from an un-navigated page (fixed).

Suite **194**. All 9 live checks green. Commits `28e8b5883`,
`20bf7c971`, `35ddfc2bf`.

**R7 candidates:** depot restock push to the coordinator surface, witness
photo-upload real file path (currently described-photo hints), supervisor
shift-summary export, Hindi/Devanagari pass over responder app strings,
demo video script for the founder.

---

## Round 7 — CLOSED (2026-08-04)

**Theme: the founder's five calls, executed.** (Founder-directed round;
the heartbeat firing closed the books and added the demo script.)

1. **Renamed to Wayside** — every user-visible string across all four
   surfaces, bot replies (EN + Hinglish), report/about/metrics/replay
   pages, boot banner. Internal identifiers untouched on purpose
   (PUKAAR_* env vars, pukaar_* storage keys, module paths, hash salt).
   One brand-assertion test updated; 194 green after the sweep.
2. **Goonj claim removed** from the deck's customer slide (founder:
   "not right") — replaced with the honest Equitech-network line; PPTX
   rebuilt from source.
3. **Telegram parked** by founder decision — telegram-setup.md carries
   the decision note; product-plan points the chat-line demo at the
   built-in /witness page. Adapter stays dormant.
4. **Demo tour artifact published** (private link) — all surfaces
   screenshotted live post-rename, engine-room inventory, numbers, the
   3-command local recipe:
   https://claude.ai/code/artifact/5ab77ba7-51bd-4da7-ac11-1eb3c46c82c3
5. **Demo script** — research/demo-script.md: the 3-minute live pitch
   walkthrough, beat by beat, with safety nets and a quotable-numbers
   list (and a do-not-claim list).

Cache 20260804g. Commit `f0bd6dc7c` + this log. Suite 194.

**R8 queue:** depot restock push to coordinator, witness real photo
upload, shift-summary export, Hindi/Devanagari pass on rider strings,
fresh adversarial sweep of rounds 5-7 code.

---

## Round 8 — CLOSED (2026-08-04)

**Theme: sweep the sweepers.** Rounds 5-7 shipped a lot of builder-written
code; a 16-agent adversarial sweep (5 finders × per-finding skeptics)
confirmed **11 of 11** claims — the parallel-build rounds were fast but
not clean, which is exactly why this loop alternates build and audit.

### Feature (partial commit `4be60fbed`)
- **Coordinator supply strip**: dry SKUs ("MED-1 dry at Station-side
  Partner Shop — riders go direct without a kit") and couriers en route
  with countdowns, in the coordinator panel; sim.restocks_view() via
  /api/state; keyed with 30s countdown buckets.

### Sweep fixes (commit `a9cbb86bf`)
- **Rider offline honesty (the P2 that mattered)**: 'I've arrived'
  showed a false success BEFORE the request was sent, and every offline
  tap died as an unhandled rejection with a dead button. api() now
  absorbs failure; buttons recover; success is claimed only after the
  server confirms; the offline shell can't clobber the saved identity.
- **Outbox thread pinning**: queued reports carry their conversation id
  from queue time — verified live that a report queued under thread A
  delivers to A even after a deep-link switch to B.
- **Idempotent sends**: client_id per logical message, reused on retry;
  API dedupes (phone, cid) for 1h, recording only after successful
  filing (a 429'd retry is not swallowed). Pinned by test.
- **Order preserved mid-flush**: new messages queue behind older saved
  ones instead of jumping the line.
- **Offline-boot witness map**: zone cached on first healthy poll; the
  precached MapLibre + street data finally renders in airplane mode.
- **XSS + overflow in turn-by-turn**: street names escaped (OSM import
  delivers arbitrary strings), long names wrap.
- **Rename stragglers**: Devanagari replies said पुकार still — now
  वेसाइड; demo-recorder captions; export filename.

Suite **196** (restocks view + idempotency pins). All 9 live checks
green. Cache 20260804i.

**R9 queue:** witness real photo-upload path, supervisor shift-summary
export, Hindi/Devanagari pass on rider-app strings, deploy dry-run
(Dockerfile → Fly.io checklist for the founder), demo video re-record
with Wayside branding.

---

## Round 9 — CLOSED (2026-08-04)

**Theme: photos become real.** The last make-believe in the witness flow
is gone — photos are now actual files, not described hints.

- **Upload path**: "📁 Upload a photo from this phone" in the witness
  photo menu → multipart POST /api/wa/photo (open, phone-validated,
  jpeg/png/webp only, 3 MB cap, global flood window shared with text).
  Files stored under PUKAAR_MEDIA_DIR with generated names; the report
  row carries the real media_ref.
- **Ops room viewing**: /api/state carries a case→photos map; the case
  detail panel links each photo, staff-gated behind /api/media/{name}
  (strict name regex — no traversal), labelled "(deleted at case close)".
- **Retention made literal**: the purge now deletes the FILE from disk,
  not just the reference — the site's privacy claim is enforced by code
  and pinned by test.
- **Real gap caught by verification**: witnesses photograph BEFORE they
  pin (text → photo → location); pre-case photos stayed orphaned
  forever. Case creation now retro-links the reporter's recent pre-case
  media. Live E2E: upload through the real file chooser → case forms →
  detail link renders → bytes serve staff-side.
- **Offline honesty**: files can't ride the localStorage outbox — an
  offline upload says so instead of pretending.
- Parked: demo video re-record — record_demo.py predates the
  keyed-render rounds (stale DOM handles); recorder repair queued.

Suite **200** (5 photo-lifecycle pins). python-multipart added to deps.
Cache 20260804j. Commit `7e53f9ee6`.

**R10 queue:** record_demo.py repair + Wayside re-record, supervisor
shift-summary export, Hindi/Devanagari pass on rider strings, Fly.io
deploy checklist, adversarial sweep of the photo path.

---

## Round 10 — CLOSED (2026-08-04)

**Theme: the demo video lives again.** Two real bugs in the recorder,
diagnosed the hard way (three takes):

1. Retrying locator actions was NOT enough — at 30× sim speed the keyed
   panels rebuild their DOM nodes every second, so Playwright's "wait
   for element to be stable" can never settle, ever. glide_click now
   measures getBoundingClientRect straight from the DOM (layout position
   is stable even while nodes are replaced) and drives the mouse to
   coordinates. This is the durable pattern for driving any 1 Hz-keyed
   UI from Playwright.
2. Captions carried three pitch violations: a GoodSAM name-drop (the
   founder's standing rule — lead with the mechanism, never a niche
   brand), a stale "103 tests" claim, and a PUKAAR closing card. Now:
   "like real emergency dispatch", "200 tests", and the Wayside
   wordmark.

Output: **docs/wayside-demo.webm** (~3.5 min, 19.9 MB, self-narrating) —
witness report → dispatch → golden run → dedup → 112 gate → the
responder phone accepting ON CAMERA with turn-by-turn steps → privacy
purge → metrics. Delivered to the founder and committed (replacing the
old pukaar-demo.webm).

Commits `d5c8a332d`, `bd0b58c0f`, + this one. Suite unchanged at 200.

**R11 queue (carried from R10):** supervisor shift-summary export,
Hindi/Devanagari pass on rider-app strings, Fly.io deploy checklist,
adversarial sweep of the photo path.

---

## Round 11 — CLOSED (2026-08-04)

**Theme: two founder-facing deliverables.**

1. **Shift handover report** — the coordinator's end-of-day export.
   svc.shift_summary(now, hours) scopes everything to cases opened in
   the window (default 12h, clamped 1-72) and rolls up, in plain
   language: reports received, people served, clinical escalations,
   still-open-hand-to-next-shift, median accept time, kit movement
   (delivered / returned unused / restocks), stock on hand + low SKUs.
   Two staff-gated surfaces — printable HTML at /shift (new supervisor
   toolbar button, check-circle icon) and JSON at /api/shift. Verified
   live against the seeded world (7 reports, 3 served, SEAS-M low),
   screenshotted; 3 tests pin window scoping, gating, hours clamp.
2. **App deploy checklist** (research/deploy-app.md) — founder-runnable
   guide to a private URL for the LIVE APP (not the static site):
   Fly.io Mumbai ~$3-6/mo with exact secrets + volume + the
   /login?token= judge link, Render/Railway as no-card fallbacks, a
   pre-show 5-point sanity check. Dockerfile now documents
   PUKAAR_MEDIA_DIR on the persistent volume (photos would vanish on
   redeploy). This unblocks the private URL the founder wanted to see.

Suite **202**. Cache 20260804k. Commit `5488d2e0e`.

**R12 queue:** Hindi/Devanagari pass on rider-app strings, adversarial
sweep of the photo path + shift export, deploy a real instance if the
founder green-lights the Fly card, GitHub Actions pages workflow for the
marketing site.

---

## Round 12 — CLOSED (2026-08-05)

**Theme: bilingual rider + a hard security sweep of my own new code.**

### Feature (commit b4707f658)
- **Bilingual rider app**: Devanagari beside every action label a Delhi
  responder taps/reads — banner, ACCEPT/Pass, the outcome grid, kit
  hints, arrived, duty toggle, waiting line. Small muted .hn class. Bug
  avoided: the 1 Hz countdown update set textContent (would wipe the
  Hindi span) — now updates only the countdown sub-label. 7 labels
  verified live to the onsite screen.

### Sweep of the photo + shift code (commit 04be2bcbb) — 9/10 confirmed
- **P1, unauthenticated DoS** (my round-9 code): /api/wa/photo's 3 MB cap
  ran only AFTER the body was spooled to disk + read into one bytes; a
  multi-GB POST could exhaust the temp volume and OOM the single worker
  (which also runs the sim). Fixed: body_limit middleware rejects on
  Content-Length before parsing (verified live, forged 5 MB → 413) +
  64 KB chunked read with early abort.
- **P2, orphaned files**: file written before wa_inbound, which can
  short-circuit on the per-phone budget → a file no report references →
  the row-driven purge never deletes it. Fixed: unlink if unreferenced,
  plus a retention backstop directory sweep.
- **P2, shift undercount**: kit counts came from the bounded 250-event
  feed. Now from the durable outcomes table; restocks labelled "recent".
- **P3s**: photo upload idempotent (client_id); control-room /shift link
  added; FastAPI title + pyproject desc de-Pukaar'd.
- Deleted a proof-of-bug test a verifier agent left in tests/; proper
  regression tests assert the FIX (413, no-orphan, sweep, dedupe).

Suite **206**. Cache 20260804m. Commits `b4707f658`, `04be2bcbb`.

**R13 queue:** GitHub Actions pages workflow for the marketing site,
adversarial sweep of the bilingual/rider changes, another pilot-readiness
feature, deploy a real instance if the founder green-lights Fly.

---

## Round 13 — CLOSED (2026-08-05)

**Theme: accessibility + i18n correctness.** The bilingual rider (r12)
was a lie to a screen reader — Devanagari with no lang markup gets
pronounced in an English voice, worse than useless for a low-literacy
responder on TalkBack.

- **lang="hi" on every Devanagari string**: the 9 rider .hn action
  labels, the EN ROUTE / AT THE PIN banner, the duty pill (switched from
  textContent to innerHTML with the responder name escaped), the
  "Who are you?" heading.
- **Chat bubbles**: any bubble whose text contains Devanagari now gets
  lang="hi" via a per-message U+0900–097F check — both the witness page
  and the control-room phone panel (so the bot replying in देवनागरी
  reads correctly).
- **role="status"** on the witness offline/queued toast (responder toast
  already had it) so status changes are announced.
- Verified live with an automated a11y pass: 10 Devanagari elements
  tagged, 0 untagged; every button/link on all four surfaces has an
  accessible name.

**Deliberately skipped** the queued GitHub Actions pages workflow: this
repo is a FORK of the is-a.dev DNS registry (the existing publish/
dnscontrol/raw-api workflows are upstream), so an auto-Pages deploy could
collide with the fork's purpose — the site deploy stays documented
manually in site/DEPLOY.md. Flagged rather than risk upstream conflict.

Suite **206**. Cache 20260804o. Commit `9f5117c41`.

**R14 queue:** adversarial sweep of the r12/r13 changes, another
pilot-readiness feature (responder roster/vetting admin view?), witness
first-contact consent line (DPDP), deploy if founder green-lights Fly.

---

## Round 14 — CLOSED (2026-08-05)

**Theme: the first broad audit since R3 — and it caught a deploy-breaker.**
6 finders across the whole system, **12/12 confirmed, all fixed**. (The
queued DPDP-consent item was already done: S-NOTICE covers the compliant
first-contact notice in all three scripts — verified, no work needed.)

- **P1 — the documented deploy was broken.** With PUKAAR_ADMIN_TOKEN set
  (what deploy-app.md tells the founder to do), the witness page + its
  /static assets + its data were ALL 401-gated → a judge opening /witness
  gets a dead page. Fixed: a scoped PUBLIC `/api/witness/state` (zone +
  the caller's OWN thread only — leaks no other chats/pins/positions) and
  opening /witness + /static + /data + /sw.js in the gate. /api/state,
  control room, supervisor, responder, exports, /shift stay gated.
  Verified live on a token deploy: witness boots + reports end-to-end,
  every staff surface 401s.
- **P2s**: /webhook inert without WA_APP_SECRET (was an open unsigned
  injection endpoint on the default demo config); body_limit requires
  Content-Length on open JSON paths (closes a chunked bypass of the r12
  DoS fix); responder api() awaits r.json() (unawaited rejection left
  buttons dead forever); responder/depot names escape into every
  innerHTML sink; retention orphan sweep gets a 60s mtime grace (can't
  delete an in-flight upload).
- **P3s**: shift_summary + run_purge cross-thread iterations snapshotted
  (R4's sweep predated both); coordinator supply strip keys on structure
  not the live countdown (was closing the assign dropdown every 30s);
  responder poll got app.js's overlap-guard + timeout; ACCEPT button
  Hindi/English lang tags un-swapped.
- P3 (routing): fetch_real_roads.py (founder's OSM importer) skips the
  per-mode connectivity check — logged for the importer, not demo-path.

3 tests updated to the correct new contract, 2 new regression tests
(witness-public-on-token-deploy, orphan grace). Suite **208**. Cache
20260804p. Commit `6b9cfecd7`.

**R15 queue:** the fetch_real_roads connectivity check, responder
roster/vetting view, deploy a real instance if founder green-lights Fly,
another feature pass. The code is now materially more deploy-safe.

---

## Round 15 — CLOSED (2026-08-05)

**Theme: pilot-readiness feature — the volunteer roster.** After two
audit-heavy rounds, a feature: the operational piece an NGO asks for
first — who can respond and are they vetted.

- **Responder roster panel** (coordinator side, supervisor + control
  room): each volunteer with vetting badge (✓ vetted / pending),
  medical marker, session served-count, and an on/off-duty toggle.
  Deactivating stops NEW offers immediately (dispatch `_candidates`
  already filters `active=1`); a job in hand runs out. svc.roster() +
  set_active(), POST /api/roster/active (staff-gated), rides /api/state,
  keyed render. Verified live: 6 vetted, toggle dims the row + updates
  the 5/6-on count, zero errors. Friendly "taken off duty" feed line;
  names escaped (kit_pickup/kit_return too — same class as R14).
- **OSM-import connectivity check** (R14 P3): tools/fetch_real_roads.py
  now runs a per-mode fallback report after writing — warns loudly if
  walk/cycle/scooter have disconnected islands that would degrade the
  router to straight lines. 0% on the shipped demo zone.

3 roster tests. Suite **211**. Cache 20260804q. Commit `7198fdf8c`.

**R16 queue:** deploy a real Fly instance if the founder green-lights the
card; a fresh sweep of r15; witness data-subject rights note; or another
feature. The product is deeply mature — 15 rounds, 211 tests, offline,
bilingual, a11y, photos, shift+roster ops views, deploy-safe, audited 4×.

## Overnight round 1 — 2026-08-05 (persona-critic audit, wave 1)

Five persona critics launched (judge, product skeptic, NGO ops, CTO,
mobile field); three reports in by round end. Every finding below was
re-verified against the live app before fixing.

**CTO report (verdict: "would survive due diligence"):**
- **P1 emergency gate misses fixed** — heart attack, stroke, drowning,
  choking, childbirth-in-progress, suicide, and the literal "cannot
  breathe" (the pattern only matched "can't") now trip the 112 gate, in
  Latin and Devanagari, with "Labour Chowk"-class place names guarded as
  non-emergencies. Golden set +15 emergencies, +4 non-emergencies.
- accept-after-bench race: dispatch.respond() re-checks active=1 before
  the CAS, so a deactivated volunteer can't accept a stale open offer.
- instruction_ids hardened both ends (allowlist in orders.py, escapeHtml
  fallback in responder.js) — closes the live-backend XSS vector.
- sim kinetic state now behind an RLock (tick / set_duty / settle_kit).
- /api/manual and sos validate responder ids (404, matching roster).
- straight-line routing fallbacks now warn loudly (once per reason) —
  matters when real OSM zones with disconnected islands get swapped in.
- category feed/detail sinks escaped (latent, enum-pinned today).

**Judge report (8/10, "this wins or podiums"):**
- "26m away" minutes/metres collision fixed — fmtDur says "26 min" now
  (also flagged independently by the mobile critic; both surfaces).
- the two-minute dead-air walk: calm boards auto-compress to 24× while a
  human-played rider is enroute and restore the founder's speed on
  arrival, with transparent ⏩/⏱ feed lines. Verified live: 6→24→6.
- ACCEPTANCE tile no longer reads 0% mid-wave (denominator = orders with
  ≥1 decided offer).
- "back on duty" on first-ever duty → "on duty".

**Mobile report:** minutes-unit fix shipped this round; the fold/contrast/
sticky-outcome-bar P1s and the rest of judge P2s (deck reconciliation,
report.py partner_1 leak, scooter-emoji string, stale demo script) are
queued for round 2 with the remaining two critic reports.

217 tests green; live calm-flow verified end to end (404s, accept via
depot, auto-pace round-trip). Cache 20260805c.

## Overnight round 2 — 2026-08-05 (NGO-ops P1 wave)

The NGO operations-director critic delivered the deepest report
("conditionally yes" to piloting). Verified and fixed its top P1s:

- **Gate precision (borderline P0):** bare "khoon beh raha hai" — the
  ordinary way witnesses describe any bleeding wound — no longer bounces
  to 112 with nothing filed; heavy-bleeding phrases (bahut/zyada/tez
  khoon, khoon ruk nahi) still gate, in both scripts. Golden set updated
  both directions. 112 bounces now surface on the /shift handover ("check
  these by hand each morning" row) — they were already durably recorded.
- **Intake terminal rung:** two unanswered location asks now adopt the
  witness's own words as a landmark-only case for the coordinator's
  request-pin rail — verified live: case filed on turn 4 with
  geo_conf=landmark instead of seven asks and nothing.
- **Dedup category guard:** cross-category near-hits stay separate cases
  (a food report 80 m from a medical case is a different person).
- **Vetting is now a gate:** offers, manual assignment, and the accept
  path all require vetting='verified' (seeds unchanged, so the demo
  behaves identically until a real roster varies).

220 tests green (3 new). Queued for r3: manual-assign consent offer,
release-and-rewave on stuck accepted orders, night-P1 held-for-morning
strip, stock-adjust endpoint, road-distance candidate ranking, mobile
CSS P1s (sticky outcome bar, AA contrast, witness fold), judge P2 doc
reconciliation + deck 217 rebuild, STOP-string honesty, investor report
(still running).

## Overnight round 3 — 2026-08-05 (mobile P1s + judge P2 reconciliation)

Mobile-field P1s, each verified at 360x740 after the fix:
- Responder outcome buttons sticky at the viewport bottom with safe-area
  padding — visible without scroll at arrival (was y=848 in a 740px view).
- AA contrast: primary CTA fills darkened (#087f08 / #2b6cbe, ≥4.5:1 vs
  3.3-3.6 before); .hn Hindi sublabels opacity 0.72 → 0.9.
- Witness composer above the fold: map height clamp(180px,32vh,320px) +
  thread 30vh in the phone block (composer bottom 652 in a 740 viewport).
- Offline thread honesty: queued reports render as dashed "🕓 saved —
  will send" bubbles; typing dots gated on navigator.onLine.

Judge P2 reconciliation:
- Deck + pitch md + proposal + demo scripts now all say 217 tests (was
  a 99/194/211 spread); proposal header reads "Wayside (formerly
  Pukaar)"; stale pukaar/demo-script.md replaced with a pointer stub to
  the current script; report handout drops the "(partner_1)" leak;
  S-PROGRESS-ACCEPTED loses the scooter emoji for walkers (🟢, all three
  language mirrors); control-room outcome chips speak the same dialect
  as the phone (English + Hindi sub); responder idle card loses its
  wrapped separator dot. Deck rebuilt (13 slides verified).

220 tests green. Cache 20260805d. Investor critic still running; NGO r3
queue (consent offers, release-and-rewave, night strip, stock adjust,
road ranking, STOP honesty) next.

## Overnight round 4 — 2026-08-05 (investor P0/P1 wave: silent failures speak)

Fifth critic (YC-partner product skeptic) reported. Verified + fixed:
- **P0 golden-run dead click**: on a calm board the golden button now
  brings a sim medical rider on shift itself (roster path, feed shows the
  join) — verified live: "golden run staged for Meena", case + offer on a
  cold board. Scenario buttons also toast the sim's own result string
  instead of discarding it.
- Auto-pace covers every accept path in calm mode (any enroute rider, not
  only manual ones) and the header clock shows a ⏩ pill while pacing.
- Coordinator assign: dropdown offers only on-duty riders ("no one on
  duty" otherwise), failures toast instead of dying silently.
- Declines are visible: feed line "passed on … — next in wave", phone
  toast "Passed — the offer moves on".
- Offer countdown speaks wall-clock ("45 s left"), not sim-minutes.
- MOCK AGENT badge → "SIM AGENT · demo"; retention purge asks before
  irreversibly deleting media.
- Investor's "refresh wipes chats" did NOT reproduce on the current
  build (state serves last-30 logs for last-6 threads; verified live).

220 tests green. Cache 20260805e. Remaining queue → r5: NGO consent
offers + release-and-rewave + night strip + stock adjust + road-distance
ranking + STOP honesty; investor P2s (offer-card story line, arrived-
from-afar flag, ID vocabulary, pause chip); mobile P2 tap targets.

## Overnight round 5 — 2026-08-05 (investor + mobile P2 polish)

- Far-arrival honesty: a manual "I've arrived" tap now carries the
  rider's real distance to the pin; beyond 300 m the feed line ambers
  ("tapped arrived — 1.4 km from the pin") and an arrived_far audit row
  is written (mechanism verified: far_m=1400 + audit row).
- PAUSED chip over the map — a stray pause click no longer silently
  freezes the "live" board.
- 44 px touch minimums for scenario/photo/quick-reply buttons on phones;
  witness input at 16 px (kills iOS zoom-on-focus); supervisor roster
  duty toggles padded; wmap-hint moved top-left off the attribution;
  responder offline identity picker explains itself instead of rendering
  an empty white box.

220 tests green. Cache 20260805f. Note: stacked heartbeats from earlier
rounds caused a port-8877 collision during verification (stale server
answered a probe) — re-verified clean on 8879; future rounds kill old
servers first. Remaining big queue → r6: NGO wave-2 (consent offers,
release-and-rewave, night strip, stock adjust, road ranking, STOP
honesty) + investor offer-card story line + ID vocabulary.

## Overnight round 6 — 2026-08-05 (NGO wave-2: coordinator rails)

- **Release-and-rewave**: accepted/onsite orders can be released back to
  the wave cycle from the case detail ("rider can't finish") — kit
  reservation returns to the shelf, the released rider stands down, the
  race-losers of the original wave become offerable again, an audit row
  (released_rewave) records it, and the feed narrates. The honest
  alternative to closing a stuck job with a false outcome.
- **Night-hold visibility**: a 🌙 "held for morning: N (oldest Xh)" chip
  over the map whenever queued orders are parked outside the dispatch
  window.
- **STOP means deleted**: S-STOP now deletes the conversation row and
  memory outright, leaves a hashed witness_stop audit entry, and a
  suppression set keeps stray post-STOP button taps silent while a fresh
  text re-opens the line — every promise in the string is now literally
  true. Old tests updated to the new contract.

222 tests green (2 new). Cache 20260805g. Remaining queue → r7: consent
offers for manual_assign, stock-adjust endpoint + UI, road-distance
candidate ranking, offer-card case story line, ID vocabulary.

## Overnight round 7 — 2026-08-06 (final feature block: consent, road ranking, stock)

- **Consent offers**: a coordinator hand-off now sends a priority offer
  the rider must still tap (the GoodSAM covenant) — riding the normal
  wave machinery so a decline honestly returns to the coordinator;
  force=True keeps the direct lock for phone-confirmed assigns (and the
  sim's own coordinator). Queue button reads "offer to".
- **Road-distance candidate ranking**: dispatch ranks by street-graph
  metres in the rider's own travel mode (haversine fallback when no
  graph) — beeline ranking had walking Meena outranking scooter Ravi on
  jobs 2.5× longer by road.
- **Stock control**: POST /api/stock/adjust (depot, sku, ±delta, reason)
  with audit row + feed line — staff can finally record real restocks,
  damage, and corrections; the sim courier is labeled "(simulated)".
- Offer card now tells the story: case short-id + the witness's first
  detail line, so the rider knows what they're accepting.

224 tests green (2 new). Cache 20260805h. All five critic reports fully
processed. Remaining nice-to-haves: ID vocabulary sweep, offer-card
road-metres display, night-P1 on-call push, per-rider tokens.

## Overnight round 8 — 2026-08-06 (workspace recovery + freshness)

The container restarted between rounds and came back with a checkout at
c61585695 (pre-overnight) — first probes made rounds 3-7 look "lost".
git fetch showed ALL overnight commits safe on origin; fast-forwarded and
re-verified every marker (glide, night chip, consent offers, sticky
outcomes, contrast, story line) present at 67ad1922e. Lesson encoded in
the loop prompts: every round now starts with fetch + ff-only before
touching anything.

Live re-run of the founder flow on the real build: offer card now shows
case id + the witness's words with an honest 30 s wall-clock countdown
(added a truncation ellipsis while eyeballing). README quickstart and
the founder guide artifact refreshed to 224 tests + the new coordinator
rails (consent offers, release-and-rewave, request-pin). Cache 20260805i.
224 tests green.

## Overnight round 9 — 2026-08-06 (road-true offer cards)

The last flagged number lie: the offer card quoted beeline metres for
jobs that route 2-3x longer. /api/state now attaches the street-graph
road distance (rider's own travel mode) to every PENDING offer, and the
card says "1952 m by road" instead of "735 m" — verified live. Beeline
remains only as the no-graph fallback. 224 tests green. Cache 20260805j.

## Overnight round 10 — 2026-08-06 (demo-tour artifact rebuilt)

Another container reset caught and recovered by the round-start
fetch/ff protocol (workspace was back at c61585695; origin had all
nine rounds). Founder flow re-verified live on the real build.

The shared "Wayside — Demo Tour" artifact still showed the pre-calm-mode
product (busy seeded board, old claims). Rebuilt it from six fresh
screenshots captured this round on commit f020b10e0: calm boot → rider
on shift → the offer with the witness's words and road-true metres →
the depot kit run on real streets → dignity at the pin → the closed
loop. Same URL, current truth (224 tests, road-true routing chips).
No code changes this round; suite green at 224.

## Overnight round 11 — 2026-08-06 (release rail live-proof + pre-demo checklist)

Live probe of the coordinator release rail on a calm board with two
riders: released mid-drive → rider stands down to idle, order re-waves
to the other on-duty rider (and the released one, by design — a dead
phone simply times out), feed narrates, audit row written. Appended the
founder's final pre-demo checklist to research/demo-script.md: pull
first (31ee9657d+), plain boot, three-screen setup, auto-pace and
golden-button instincts, the release rail as the honest unstick, the
purge closer, and key rotation after the demo. 224 tests green.

## Overnight round 12 — 2026-08-06 (founder summary + deck 224)

Wrote the founder-facing overnight summary at the top of this log (pull
target, headline changes by theme, artifact links, checklist pointer)
and caught the deck's stale title chip — build_deck.js + pitch md said
217 tests; now 224, deck rebuilt. 224 tests green.

---

## 2026-08-09 · founder session: demo video, map frame, live review

**Demo video** (`research/pitch/wayside-demo.mp4`, 50s, fully English):
the founder's storyboard shot live with Playwright — witness
message → pin → photo (the photo files the report) → control-room ping →
rider accepts → depot medkit run on streets → outcome served → witness
closure. Phone surfaces composed in a device bezel; title/close cards.

**Founder bug ("map doesn't render when I scroll out") — fixed** in
`45f0ae120`: beyond the zone's GeoJSON the world was bare background
color. `buildStyle` now dims outside a ~1.12×-radius disc and labels the
boundary "WAYSIDE PILOT ZONE", both maps, both themes. An independent
reviewer agent reproduced the pre-fix symptom live and verified the fix.

**Sim pacing** (same commit): auto-pace re-engaged every tick, clobbering
a manually chosen slower speed mid-drive back to 24×. Now edge-triggered
on travel start — the founder's speed pick sticks.

**Live human-style review** (background agent, 94 screenshots, full
witness→rider→closure loop three ways): report verified and processed —
- P1 double-click/double-tap zoom teleported the witness pin (the
  dispatch location) — click now places on a 300 ms fuse that a dblclick
  cancels, witness + control room.
- P2 📍-with-no-pin fabricated a random location and shared it silently —
  now an honest nudge, nothing sent.
- P2 rider "Recent activity" pinned to the session's six oldest events
  (`slice(-6)` on a newest-first feed) — now `slice(0, 6)`.
- P2 /shift "112 redirects" counted every case-less report row (phantom
  emergencies on the one number a human hand-checks) — redirects now
  write an `emergency_redirect` audit row and the handover counts those.
  New regression test.
- P2 90-day cells toggle was a silent no-op on an empty board — now
  toasts "no aggregates yet" so the privacy story never looks broken.
- P3 maxZoom 18.5 overzoomed past data density (flat void) — 17.5.
- P3 rider footer tagline collided with the SOS pill ≤430px — hidden.
Deliberately deferred (P3 polish): scenario-button thread-switch cue,
"routed" chip on wave-exhausted orders, autoDuty consent cue, post-accept
distance jump explanation, vocab sweep, pan rubber-band feedback.

Suite: **225 passed** (was 224; +1 regression test). Cache `20260805l`.
