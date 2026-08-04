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
