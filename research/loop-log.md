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
