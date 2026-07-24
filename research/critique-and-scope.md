# Critique and scoping: the "Street Aid" concept

The concept has three layers, and they deserve to be judged separately:

1. **Detect** — street/traffic cameras + CV find people who need supplies.
2. **Fulfil** — delivery fleets (Zomato, Blinkit, Swiggy, Uber Eats) carry aid kits to them, ~1 in every N deliveries.
3. **Fund/Supply** — platform CSR and NGOs (Goonj) pay for and assemble the kits.

**Verdict up front:** layer 2 is proven and layer 3 is available — nobody has wired them together for street-level individual aid, and that orchestration is where the real value is. Layer 1, the camera part, is the weakest, most dangerous, and least necessary piece of the plan. Keep the mission, replace the sensor.

Evidence and links for the claims below are in [landscape-findings.md](./landscape-findings.md).

---

## The holes

### Layer 1: Detection via street cameras

**1. You can't get the cameras.** Traffic and speed cameras in India are operated by state police and municipal smart-city command centres (ICCCs) through vendors. There is no public API, no data-sharing program for startups, and no realistic path for a private individual to get live feeds — Bengaluru's Safe City contract sets a ₹5 lakh penalty *per unauthorized feed access*, and the only documented third-party access anywhere is government contracts and research MoUs. This isn't a "later" problem — it kills the stated v1 outright.

**2. Even with access, the cameras can't see what you need.** Enforcement cameras are aimed at license plates and the roadway, not sidewalks. They're optimized for plate legibility (narrow field, IR flash, motion-triggered crops). A bandaged, bleeding foot on a pavement is far below the resolvable detail of any traffic camera, at the wrong angle, often at night or in rain. Realistic detection classes from public CCTV are coarse: "person lying down", "encampment", "person present in unusual place/time" — not "needs antiseptic and fresh wrapping". The medical judgment you performed on that street used human-level context that this imagery does not contain. The hard number: San Jose's pilot — the only real attempt at anything adjacent — scored **97% on potholes and 10–15% on "is someone living in this car"** with the same pipeline. Object detection works; inferring human circumstance from imagery doesn't.

**3. Even if it worked, it surveils people who never consented — and the data cuts both ways.** A database of "here are the city's most vulnerable people, updated in real time" is exactly the dataset used for encampment sweeps and, in India — where begging is still criminalized under state laws in many places — for enforcement. This is not hypothetical: Delhi demolished shelters ahead of the G20 (2023), Hyderabad recorded biometrics of rounded-up beggars (2017), and Indore has been running a CCTV-monitored "beggar-free" drive since Jan 2025 that files FIRs against people *giving* alms. San Jose's 2024 encampment-detection pilot drew sustained civil-liberties backlash for precisely this reason — and the city removed the encampment-detection component in Sept 2025, citing privacy concerns, while keeping pothole detection. India's DPDP Act 2023 adds legal exposure: you'd be processing images of identifiable people and *inferring their health condition* without consent. And it collides head-on with Goonj's ethos, which is built on the dignity of the receiver — "we watch poor people with cameras and dispatch charity at them" is a sentence Goonj would likely never sign.

**4. False negatives are worse than false positives.** A false positive wastes a kit. A false negative — or worse, a *successful* detection that resolves as "kit delivered, case closed" — can substitute a Band-Aid for the wound debridement, antibiotics, or hospital referral the person actually needed, and remove the social pressure for a human to stop. The man you saw needed supplies *and probably a clinical look at that foot*. Any system that "handles" him with supplies alone can actively delay real care. Flagging medical need from images and acting on it also starts to look like triage software, which has a regulatory boundary (CDSCO/SaMD in India, stricter elsewhere).

### Layer 2: Fulfilment via delivery fleets

**5. "1 in 5 deliveries" breaks gig economics as stated.** Riders are paid per drop under time pressure; an unpaid or under-paid detour is a pay cut imposed on the lowest-paid person in the system. Platforms will also never tax their own throughput that way. The fix is known and proven: charitable deliveries as *normally paid gigs funded by a CSR budget* — this is exactly DoorDash's Project DASH model (8M+ deliveries, Dashers paid normal rates), and Blinkit's 10-minute ambulance (25 vehicles in NCR by Jan 2026) shows Indian quick-commerce will build humanitarian logistics lines when funded. So the mechanic survives, but reframed: not a tithe on riders, a funded order type. Note also that this is now regulated territory: Karnataka's gig-worker act (in force May 2025) requires 14-day notice of any contract/task change and algorithmic transparency on assignment and pay — an "aid drop" order type is a formal change, not a feature flag.

**6. The recipient has no address, moves, and may refuse.** Pins go stale in hours; the person may be asleep, elsewhere, or decline help from a stranger in a delivery uniform. Riders are not trained for consent-sensitive interactions with people in crisis, and there are safety concerns in both directions, especially at night. Plus-codes (used by "Addressing the Unaddressed" for Kolkata slums) solve *addressing*, not *staleness* or *consent*. For v1, delivering kits **to outreach workers** (who know the people, hold trust, and carry medical judgment) beats delivering to the person directly.

**7. Drivers doing "a good serve" is also a liability question.** If a platform routes a worker to a person flagged as possibly injured and something goes wrong — for either party — whose problem is that? India's Good Samaritan protections cover bystanders at road accidents, not an organized dispatch system. Platforms' legal teams will ask this before their CSR teams answer anything.

### Layer 3: Funding and supply

**8. CSR pilots die quietly.** Platform CSR is real money but fashion-driven; programs get one budget cycle to prove a number. Without a hard metric (cost per *verified* need served, not kits flung), the program is a press release that expires. Goonj's material supply is genuinely strong for the non-medical kit contents (clothing, tarpaulin, footwear) — but antiseptic and dressings are purchased goods, so someone still writes cheques, and medical items inside a "kit" raise the bar on who's allowed to hand them out: anything beyond OTC/first-aid items trips the Drugs & Cosmetics Act (e-pharmacy rules still un-notified), so kit contents must stay strictly OTC. One ready-made funding rail worth knowing: the ₹1–10 checkout donations on Zomato and Blinkit already fund Feeding India at 200K+ meals/day — the mechanism for micro-funding kits exists in-app today.

### Cross-cutting

**9. Verification and measurement.** Feel-good deliveries ≠ outcomes. Without a human verifying need before dispatch and confirming receipt after, you cannot distinguish impact from theatre — and you cannot keep funders.

**10. The medical part already has an owner.** Wound care for people on the street is the domain of street-medicine teams and mobile medical units, plus systems like Delhi's DUSIB winter-rescue vans that respond to citizen reports. If they don't exist in your target city, that's the gap; if they do, your system should *feed and supply them*, not route around them.

---

## What survives

- **The fulfilment rail** — funded, normally paid charitable deliveries on gig fleets. Proven pattern (Project DASH), demonstrated Indian appetite (Blinkit ambulance, Feeding India).
- **The kit** — a standardized, cheap "street aid kit" (wound-care basics, ORS, socks, tarpaulin/umbrella by season) with Goonj assembling from surplus material + purchased medical items. Nobody has standardized this for India.
- **The needs signal — but humans, not cameras.** The cheapest, most accurate, most consent-compatible sensors already on every street are *the riders themselves* and ordinary citizens. A one-tap "person needs help here" flag (rider app or WhatsApp bot) generates exactly the geo-tagged report you wanted cameras for, with a witness attached, no CCTV access required, and no surveillance database created. This pattern already works in India: Delhi's Rain Basera app (photo → GPS → rescue-van dispatch) and No Food Waste's "hunger spots" (citizen pins → NGO verifies → food delivered to the spot, 285k+ fed) are live proof.
- **The orchestration layer** — report → NGO verification → kit dispatch or outreach-van routing → outcome logging. This end-to-end loop does not exist anywhere we could find, and it is the actual product. The StreetLink numbers (170k reports, person found only 23% of the time, ~5% housed) say exactly where such systems die: verification and follow-through, which is why the loop — not the reporting front end — is the thing to build well.

CV can re-enter later, narrowly: coarse "person down" detection on *partner-owned* cameras (outreach vans' dashcams, consenting shopfronts) as an *assist* that always resolves to a human before any action — never on government feeds, never inferring diagnoses. The acceptable framing is proven by Seoul's bridge-CCTV rescue system (~1,270 dispatches in 2025, 99% survival, publicly celebrated): narrow emergency class → human confirms → human responds. "Person collapsing" detection is even commercially available in India (Videonetics, already running Andhra Pradesh's 15,000-camera network) — the tech will be purchasable when, and if, the loop earns the right to use it.

## Scoped MVP — 90 days, one city (Delhi, because Goonj HQ is there)

**Weeks 1–3 — kit + partners.** Define kit v1 with Goonj and one street-medicine / outreach partner (they set the medical contents and the escalation rule: "wound → also alert clinical team"). Assemble ~200 kits. Cost target under ₹300/kit.

**Weeks 3–6 — reporting + dispatch.** WhatsApp bot (Gupshup/Twilio) for reports: location pin, optional photo, category. A dead-simple dashboard (a sheet + map is fine) where the outreach partner verifies and dispatches. No custom apps, no CV.

**Weeks 6–12 — fulfilment experiment, two arms.**
(a) Outreach team carries kits on routed rounds informed by reports.
(b) Small paid-delivery arm: local riders paid normal rates from a pilot budget to deliver kits *to the outreach worker on site* (test the platform rail without putting riders in the caregiver role).
Approach Zomato/Blinkit CSR *after* you have arm-(a) data, not before — you'll be one pilot deck among hundreds otherwise.

**Metrics.** Reports/week; % verified as real need; % accepted by recipient; median time report→aid; cost per verified need served; % escalated to medical care.

**Kill criteria (decide them now, in writing).** E.g.: verified-need rate < 40% (signal too noisy); acceptance < 50% (model is undignified or mistargeted); cost per verified need > 3× kit cost (rail too expensive); outreach partner can't absorb the flow (you're generating work, not help).

**Explicitly out of scope for v1:** government camera feeds, automated detection, medical triage claims, delivering directly to unverified strangers.

## Why this is still worth doing

Nothing end-to-end exists. The pieces (reporting apps like StreetLink; charity-delivery rails; NGO material engines like Goonj; street medicine) exist separately, in different countries, unconnected. The wedge is the loop, India-first, with a real NGO anchor — and a founder with a Goonj relationship is unusually well-placed to build exactly the part that matters. The camera idea was the least valuable part of the vision; the vision survives without it.
