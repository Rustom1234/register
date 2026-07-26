# Pukaar demo — recording script (~2½ minutes)

Setup: `python -m pukaar`, open http://127.0.0.1:8877 full-screen,
speed at 6×. On a normal connection the map shows dark CARTO tiles of
Nizamuddin; screen-record at 1512×920 or larger.

**0:00 — Cold open on the control room.** Cursor idle. Say: *"This is
Pukaar — a witness-powered street-aid network. One WhatsApp number, an AI
triage layer, and the nearest trusted NGO responder."* Point at the zone
circle and the responder initials drifting on patrol.

**0:15 — Be the witness.** In the phone, type
`Bhaiya flyover ke neeche aadmi ghayal hai, patti se khoon aa raha hai`
and send. The bot replies with the privacy notice and asks for location.
Click the map to drop the 📍 pin, press the phone's 📍 button. Press 📷
(sends the wrapped-foot photo). Tap "Abhi / just now". Say: *"Four steps,
under ninety seconds — the funnel research says anything longer loses the
witness."*

**0:45 — Follow the case.** The feed shows: new case (medical), order
MED-1 · P2 · 🩺 clinical flag. Say: *"The agent extracted the category, but
the clinical flag is enforced in code — a low-confidence model can raise
concern, never lower it."* Watch wave 1 fan out to the two nearest
responders — *"GoodSAM's pattern: parallel offers, first accept wins."* A
responder turns blue-ringed and moves along the dashed line.

**1:15 — Click the case** in Open Cases. Show the card: DIGIPIN
(*"India Post's new 4-metre geocode — no address needed"*), witnesses,
kit, provenance line (*"every record is HMAC-tagged: witness, agent, or
responder — the agent's guess can never impersonate a human"*), and the
timeline filling in.

**1:35 — Dedup.** Press "👥 3 witnesses, same spot". Feed shows
`witness #2 / #3 merged (dedup)`. *"Three good Samaritans, one case, one
kit — not three."*

**1:50 — The safety line.** Press "🚨 Emergency text (112 gate)" or type
`aadmi behosh pada hai!!`. The reply is instant and fixed; the feed logs
*emergency → fixed 112 reply, no agent involved* in red. Say: *"Emergencies
never touch a model. That string is hard-coded, and the test suite fails
the build if this gate ever misses."*

**2:10 — Close on the numbers.** Zoom on the tiles: served count rising,
acceptance %, median accept time, kits depleting. Press 🧹 purge and show
the retention line. Say: *"Outcome metrics because feel-good deliveries
aren't the goal — and a retention job because the safest database is the
one that doesn't exist. This demo runs offline on a mock agent; with an
API key the same pipeline runs on Claude with structured outputs."*

Fade out on the map with responders moving.

Tips: 12× speed compresses waits between beats (the header select);
pause ⏸ while you talk over a still frame; the conversation dropdown lets
you show a scenario witness's phone too.
