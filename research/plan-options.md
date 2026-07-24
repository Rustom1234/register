# Plan options — three versions grounded in the research

## What the research says, in eight lines

1. **Nothing anywhere closes the loop** report/detect → verify → deliver aid to a person on the street. The loop is the product; every layer of it already exists separately.
2. **Cameras are a dead end for v1**: no feed access (police/ICCC-controlled, ₹5L penalties), can't resolve "needs wound care" (San Jose: 10–15% on an easier task; component shut down Sept 2025), and the data endangers the people it's meant to help (Indore's CCTV begging crackdown, G20 demolitions, DPDP Act).
3. **Human reporting works and is already Indian practice**: Delhi's Rain Basera app (photo → GPS → rescue van), helpline 14461, and No Food Waste's hunger-spots (pin → NGO verifies → food delivered to the spot, 285k+ fed).
4. **The delivery rail is proven** when riders are paid normal rates from a program budget (DoorDash Project DASH, 8M+ deliveries) — never as unpaid detours ("1 in 5" dies on gig economics and now on gig law, e.g. Karnataka's 2025 act).
5. **Indian q-commerce will do street-level medical logistics** (Blinkit ambulance: 25 vehicles NCR, Jan 2026) and **in-app micro-donations already fund aid at scale** (₹1–10 checkout donations → Feeding India, 200K meals/day).
6. **Goonj fits as kit factory and dignity anchor**, not as camera-charity: their ethos is "charity kills dignity"; their winter drive (Odha Do Zindagi) already touches people sleeping on roads.
7. **Kits must stay OTC/first-aid** (Drugs & Cosmetics Act) and every wound-type case needs escalation to street-medicine/outreach teams (Delhi has them: 16,000+ documented street consults).
8. **Follow-through is where these systems die** (StreetLink: 170k reports, person found 23%, housed ~5%). Verification, outcome logging, and cost-per-verified-need are the metrics that keep funders.

Full evidence: [landscape-findings.md](./landscape-findings.md) · full critique: [critique-and-scope.md](./critique-and-scope.md)

---

## Version A — "Supply Line" (lowest risk, fastest to real impact)

**Thesis:** Don't find new people in need yet — supercharge the people who already find them. Build the standardized kit and the logistics that existing outreach systems lack.

**How it works**
1. Design a ~₹300 **street aid kit** with Goonj + one outreach/street-medicine partner: OTC wound-care basics (antiseptic, dressings, gauze, gloves), ORS, socks, soap; seasonal add-on (umbrella/tarp in monsoon, blanket in winter). Goonj assembles from surplus material + purchased medical items; the partner sets contents and the escalation rule ("open wound → clinical team visit").
2. Outreach teams (NGO vans, and in Delhi potentially DUSIB's 15–16 winter rescue vans) carry kits on their normal rounds and log each handover on a dead-simple form: location area, need category, accepted/refused, escalated y/n.
3. A **paid restock loop**: local riders (any fleet, paid normal rates from the pilot budget) ferry kit cases from Goonj's processing center to outreach teams in the field. This quietly tests the delivery rail without ever putting a rider in front of a vulnerable stranger.

**You build:** the kit spec, a logging form + dashboard (Google Sheet + map is genuinely enough), and the restock dispatch flow. No app, no CV, no public anything.

**90 days, ~₹3–5L** (200–500 kits, delivery fees, contingency). Wedge moment: Delhi winter, when Odha Do Zindagi and DUSIB vans are already running.

**Why the research supports it:** the medical part already has owners who lack supplies and routing, not mission; delivering to workers avoids every consent/safety/liability hole; Goonj partnership fits their ethos exactly.

**Main risk:** it's invisible — a supply-chain improvement, not a product. If the partner is weak, you're a warehouse. **Success unlocks:** trust, baseline data (needs per km², acceptance rates, cost per kit delivered), and standing to run Version B.

---

## Version B — "Signal Loop" (the recommended core product)

**Thesis:** Build the loop nobody has built: report → verify → dispatch → outcome. Humans are the sensor; the No Food Waste pattern, generalized from food to aid with medical escalation.

**How it works**
1. **Report:** WhatsApp bot (Gupshup/Twilio, no app install) — anyone sends a location pin + optional photo + one-tap category (injury / weather / hunger / shelter). Later, the growth hack: pitch one delivery platform to add an opt-in **one-tap "person needs help here" flag for riders** — 100k human sensors already passing every street, zero cameras.
2. **Verify:** reports land on the outreach partner's dashboard; a worker (or trained volunteer) confirms within hours. Wound category auto-alerts the street-medicine team. Privacy by architecture: pins expire in 72h, no names, no faces stored, aggregate-only heatmaps.
3. **Dispatch:** verified need → kit goes out via the Version-A supply line — outreach team when available, funded rider drop *to the outreach worker on site* when speed matters.
4. **Outcome:** every case closed with found/not-found, accepted/refused, escalated — the StreetLink-lesson metrics, tracked from day one.

**You build:** the bot, the verification dashboard, the dispatch integration, the metrics spine. Version A is literally this system's fulfilment backbone, so run A first or in parallel.

**6 months, ~₹8–15L.** Partners: Goonj (kits) + street-medicine/outreach org (verification & response) + optionally DUSIB (forward their 14461-type reports in one pilot zone).

**Why the research supports it:** report-to-dispatch is proven Indian practice (Rain Basera, No Food Waste); ML-on-reports triage has precedent (DSSG × Homeless Link) and gives you a legitimate AI roadmap; no DPDP exposure worth naming; the loop's absence is the confirmed white space.

**Main risks:** report volume could be low (seed via RWAs, security guards, auto drivers) or junk-heavy (StreetLink's 23% found-rate — mitigate with photo + freshness prompts and fast verification); partner capacity is the real throughput limit — never generate more verified need than the partner can serve.

**Kill criteria (write them down now):** verified-need rate <40%; acceptance <50%; cost per verified need served >3× kit cost; partner backlog growing week over week.

---

## Version C — "Aid Drops" (the big swing — productize it inside a platform)

**Thesis:** Project DASH for street aid, built with a platform instead of around one. Zomato/Blinkit already have the riders, the ₹1–10 checkout-donation rail, Feeding India's NGO network, and demonstrated appetite for humanitarian logistics (ambulances). Make "fund a street aid kit" a checkout option and "deliver an aid drop" a normally-paid order type routed to NGO-verified spots.

**How it works:** your Signal Loop supplies verified need-spots; the platform's CSR/foundation funds kits (checkout donations + CSR budget); Goonj supplies kits into dark stores; riders opt in to aid-drop orders at normal pay, delivering to outreach workers or NGO-marshalled distribution points. You are the verification + orchestration layer in the middle — the thing the platform can't credibly build itself.

**Why the research supports it:** every ingredient exists inside Zomato/Blinkit today (donation rail funding 200K meals/day, ambulance precedent, Feeding India's 145+ NGO partners); no platform anywhere has done the last 100 meters to street level — first-mover CSR story they can't get elsewhere.

**Main risks:** you become a BD project — 6–12 month platform sales cycle, CSR fashion risk, single-platform dependency; gig-law compliance is the platform's burden but your timeline (Karnataka's 14-day-notice + algorithmic-transparency rules make "aid drops" a formal program, not a feature flag); and pitching without data means being one deck among hundreds.

**Precondition:** walk in with Version B's numbers — "X verified needs served at ₹Y each, Z% acceptance, escalation working" — not a concept.

---

## Recommended sequence

**A → B → C is one plan at three altitudes.** Start Supply Line now (it's a phone call to Goonj and one outreach org plus a kit spec); stand up the Signal Loop on top of it within the first quarter; take the loop's data to a platform in month 6+. CV stays parked until the loop earns it — and then only Seoul-style: coarse "person down" alerts on partner-owned cameras, human-confirmed before anything moves (the tech is already purchasable in India — Videonetics — when that day comes).

The first concrete step for all three versions is identical: **one conversation with Goonj** about kit assembly and whose outreach teams they trust in your pilot city — your existing link makes you unusually placed to have it this week.
