# Pukaar — build log

One autonomous build session, 2026-07-26, on branch
`claude/street-aid-research-4xqdpu`. Every batch kept the suite green;
the test count tells the story.

| Batch | What landed | Tests |
|---|---|---|
| 1 · Core system | 112 gate (100%-recall blocking test), ≤4-step intake FSM, mock + Claude backends (structured outputs), code-enforced conservative medical defaults, GoodSAM-style parallel-wave dispatch with first-accept, geo-cell dedup, DIGIPIN codec, HMAC channel provenance, retention purge, deterministic sim | **39** |
| 2 · Control room | Leaflet dark map (validated palette), witness WhatsApp phone, scenario buttons, live ops feed, stat tiles, case detail with timeline, purge button; Leaflet vendored; FastAPI body-model fix | 39 |
| 3 · Ops depth | Responder phone (manual takeover), coordinator queue (manual assign), night-mode dispatch windows + S-EXPECT-NIGHT, metrics & kill-criteria page, WebAudio event sounds, session export, WhatsApp Cloud API transport (tested parser + verify endpoint + senders), GitHub Actions CI | **51** |
| 4 · Reach | Voice-note transcript flow (gate applies to speech), Devanagari string table + toggle, session replay page | **55** |
| 5 · Trilingual | Full English table + per-conversation auto language mirroring (en/hinglish/deva), 4-way override | **59** |
| 6 · Cinema & supply | Golden-run scenario (guaranteed clean P1 arc through the real pipeline, seed-repeatable), inventory thresholds + automatic courier restock rail, bubble timestamps + typing dots, post-report intake fix (stray taps absorbed; fresh messages open a new report) | **65** |
| 7 · Launch ergonomics | `make demo` + `PUKAAR_SEED_DEMO` photogenic boot staging, flex-overlap layout fix found by the Playwright smoke, narrow-viewport stacking, replay dark-canvas fallback | **66** |
| 8 · Pitch grade | about.html story page, printable `/report` session handout, map wow (category emoji badges, responder trails, golden-run follow camera) | **69** |
| 9 · Consolidation | Dead strings removed (S-NIGHT, S-UNKNOWN), stale docstrings fixed, `PUKAAR_DB` persistence wired, CHANGELOG, research docs synced | **69** |
| 10 · Demo film | Self-narrating recorded video (`docs/pukaar-demo.webm`, injected cursor + captions; reusable `scripts/record_demo.py`); webhook voice notes flow as `kind=voice`; metrics↔report↔about cross-links | **70** |
| 11 · Hardening | Load test (300 cases) found + fixed a decision livelock (per-offer timers) and the parked needs_coordinator backlog (sim now plays the coordinator via `manual_assign`); dispatch invariant fuzz suite across 10 seeds; tick-time budgets; Dockerfile + `make docker-demo`; `PUKAAR_HOST` | **72** |
| 12 · Consolidation | aria-labels on all icon controls, `:focus-visible` states, `prefers-reduced-motion` guards; recorder script repo-ized; docs synced | **72** |

Verification cadence: full pytest per batch + Playwright smoke sessions
(seeded boot, golden run at 30×, case detail, manual responder takeover,
replay round-trip, about/report pages, narrow layout) — zero JS errors
at every checkpoint.
