# Wayside — v1 product plan (the non-technical view)

What we're building next, phase by phase, described as **what you will
see** at the end of each phase — not how it's wired. Each phase ends with
something you can open, click, and show to an NGO director.

The direction this plan answers (from the founder):
English-perfect first · riders get real notifications · costs broken down
· a flawless public website · a Google-quality map with real road routing
· the rider side as a mobile-style app · a real chat line (WhatsApp or
equivalent) · kit storage optimised across NGO locations · safety and
tracking throughout.

---

## Phase 1 — The map becomes real

**You will see:** the supervisor dashboard drawing a light, clean,
Google-looking street map — white roads, readable labels, subtle parks
and water — instead of the dark grid. Riders move **along actual Delhi
streets**, turning at corners, never cutting through buildings. Every
moving rider has a drawn route and a live ETA ("Meena · 4 min"), and the
ETA is honest about how they're moving: walking, cycling, or scooter.

**Plain-language notes:** Google's own map can't be embedded without a
paid key, so we build the closest thing: the same open street data that
powers most map apps (OpenStreetMap), restyled to Google's visual
language, with our own routing engine over the pilot zone's street
network. The demo ships with the **real Nizamuddin streets** — 1,432 road
segments surveyed by OpenStreetMap contributors and imported by
`tools/fetch_real_roads.py`, plus the real building footprints, the
railway, Humayun's Tomb and Sunder Nursery — and the real arterials of
Delhi around them for 10 km in every direction. Riders route on the
streets that are actually there. Side by side with Google Maps, it should
read as the same species, because underneath it is the same survey.

## Phase 2 — The rider side becomes a real mobile app

**You will see:** on a phone, the rider opens the app link once, taps
"Add to Home Screen," and from then on it's an app — icon, full screen,
no browser chrome. When an offer comes in, **the phone buzzes with a
notification even if the app is closed**. Tap it → the offer card →
Accept → a map with the route and the pickup instruction. Everything in
clean, perfect English first (Hindi stays available for witnesses).

**Safety and tracking, visible:** the coordinator sees each on-duty
rider as a moving dot with a breadcrumb trail; if a rider stops moving
mid-job for too long, the dashboard raises an alarm on its own. The
rider gets a persistent "🆘 alert coordinator" button. Every case keeps
a tamper-evident audit trail from first message to outcome.

## Phase 3 — Kits become physical (depot network)

**You will see:** NGO locations on the map as depots, each showing what
it holds ("Nizamuddin office: 12 medical · 8 food · 5 monsoon"). When a
case comes in, the system chooses the rider **and** the pickup point
together — the offer says "collect MED-1 at the Basti clinic on the way
(+3 min)" and the ETA includes that detour. Stock ticks down as kits go
out; a depot running low turns amber and the supervisor gets a restock
prompt; a weekly suggestion says "move 5 medical kits from depot A to
depot B — that's where demand is."

## Phase 4 — A real chat line the public can message

Three routes, honestly laid out:

1. **Real WhatsApp number** (the destination). Needs a Meta business
   verification that only you can do — I write you the exact
   step-by-step; the code side is already built and waiting for the
   credentials. Free at pilot volume (Meta's free monthly conversation
   tier covers a pilot), then fractions of a rupee per message.
2. **Telegram bot** — PARKED (founder decision 2026-08-04; the built-in
   `/witness` web page is the demo/test chat line). A real, public,
   free-to-run chat line that can be live in days — same brain, same
   flow, no approval queue. Lets field testing start while Meta's
   verification grinds.
3. **The built-in web chat** (what exists today) stays as the demo and
   fallback.

**You will see:** a QR code on your phone screen; scan it with a normal
phone; talk to Wayside for real; watch the case appear on the dashboard.

## Phase 5 — The public website

**You will see:** a single clean page at a proper domain — the name, the
tagline ("see it, send word"), how it works in three steps, the privacy
promise in plain words, live-looking product shots, the pilot's real
numbers, and a "partner with us" contact. Flawless on a phone. Perfect
English. This is the page a funder lands on after your pitch, and it
must feel inevitable rather than scrappy.

## Phase 6 — The money page

**You will see:** a one-page cost breakdown a funder can read without
help: one-time costs (kits, phones if any, domain), monthly running
costs (hosting, messages, map data: ~zero), cost per person served
against the ₹900 kill line, and an 8-week pilot total. Every number
sourced or marked as an estimate.

---

## The order and why

1 → 2 → 3 are the product core (map, riders, kits) and build on each
other. 4 (chat line) runs in parallel because its slowest part is Meta's
queue, not our work. 5 and 6 are presentation and can land alongside.
Every phase ends demoable.

## Decisions only the founder can make

- **Depot list:** which NGO locations hold kits (names + rough
  addresses), or bless 3 placeholder depots for the demo.
- **Meta verification:** willing to do the WhatsApp business
  verification when the step-by-step is ready? (Telegram needs no such
  step.)
- **Domain name:** what the website should live at (wayside.org.in,
  waysideaid.org, …) — needs a ~₹800–2,000/yr purchase made by you.
- **Rider hardware:** confirm riders are on Android (changes nothing
  big; iPhones need one extra install step for notifications).
- **Name on the site:** confirm "Rustom Dubash" appears as founder.

## Standing constraints (unchanged)

No paid API keys anywhere in this repo — the map, routing, notifications
and Telegram path are all built keyless/free by design; the WhatsApp
path uses Meta's own free tier with *your* credentials, never a paid AI
key. English-perfect is the new default register for every screen.
