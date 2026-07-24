# Solo-buildability: how far B and C go before the first pitch

Evaluation question: building alone — no NGO signed, no platform meeting, personal budget — how much of each system can exist and *operate* before you ever pitch anyone?

**Verdict up front:**
- **Version B (Signal Loop): ~75% solo-buildable — and the 75% is the product itself.** You can be running the world's only working report→verify→serve loop, alone, in one zone, within about a month. The walls are clinical care, scale, and legal wrapper — none of which block a functioning micro-pilot.
- **Version C (Aid Drops): ~30% solo-buildable, but ~80% solo-de-riskable.** Its platform-owned components (checkout rail, order type, in-app flag) cannot exist without the pitch — but every risky assumption behind them can be tested solo, cheaply, disguised as parts of B. C isn't something you build independently; it's something you *prove* independently.

The strategic conclusion: **B is C's independence.** Every week of solo B operation converts C's pitch from "believe my concept" into "here are my numbers." Build B solo; run C's simulations inside it; pitch late, with data.

---

## Version B — component ledger

| Component | Solo? | Notes |
|---|---|---|
| WhatsApp reporting bot | ✅ Fully | Sandbox/test number via Gupshup/Twilio on day 1. Production WhatsApp Business API needs a registered business — until then, the jugaad MVP is a normal WhatsApp number you answer manually, or a QR → tiny web form. Reporters cannot tell the difference, and manual handling at <20 reports/week is *better* (you learn the message patterns before automating them). |
| Verification dashboard | ✅ Fully | Sheet + map view, or Appsmith if you want statuses and expiry automation. A day of work. |
| Aid kits, v1 (50–100 units) | ✅ Fully | Pharmacy wholesale run: antiseptic, gauze, bandages, gloves, ORS, soap, socks, rain sheet ≈ ₹300/kit → ₹15–30k for the pilot stock, packed at home. **Goonj multiplies this later; it does not unblock it.** |
| Report seeding, one zone | ✅ Fully | ~₹5k of QR posters at chemists/tea stalls, RWA WhatsApp groups, chatting up security guards and auto drivers. Needs hustle, not permission. Pick a 2–3 km² zone you already move through daily. |
| Verification legwork | ✅ At micro-scale | You are the coordinator: a report comes in, you go look — daylight hours, walkable radius. A founder who has personally verified 80 reports is unfakeable in a pitch. |
| Non-medical handovers (rain gear, socks, soap, ORS, food) | ✅ With guardrails | You're a citizen giving aid — legal and ordinary. Daytime, public places, ask before giving, ideally bring a friend. |
| Wound / medical cases | ⚠️ Refer, never treat | Solo rule: you do not do wound care. You log it, give the non-medical items, and route to what already exists — 112 if acute, the mobile medical van schedules, Delhi's 14461 — and record the referral outcome. Real clinical *follow-up* (the Thursday dressing change that actually heals the foot) is the first thing you genuinely cannot do alone. |
| Paid rider dispatch | ✅ As a customer | Porter/Borzo to a pin is just… using their product. No partnership, no pitch. Every run generates the cost-and-latency data C's pitch will quote. |
| Outcome metrics spine | ✅ Fully | Found rate, acceptance rate, time-to-verify, ₹ per verified need — designed on day 1, and the pitch pack writes itself. |
| Sustained coverage / volunteers | ❌ Wall | Beyond ~20–30 reports/week or one zone, you need an NGO's field capacity. |
| Public fundraising | ❌ Wall (legal) | Collecting donations from the public properly needs an entity (trust/Section 8) and 80G; ~2–3 months of paperwork when you choose to. Until then: self + friends funding costs directly. |
| Liability/identity wrapper | ❌ Wall (procedural) | Same entity solves it; not needed for a personal-scale pilot, needed before MoUs. |

**Where B forces the first pitch:** the wound-care loop. Around week 5–8, when your log shows "X% of verified cases are wounds I could only refer," you take exactly that number to one street-medicine / outreach NGO. That's pitch #1 — and it's a warm, low-stakes conversation with an org that gains supplies and signal, made with data no one else in India has.

**Solo timeline and cost to that point:** weeks 1–2, bot + dashboard + 50 kits (~₹35k); weeks 3–8, live operation in one zone (~₹20–30k more incl. courier runs and printing). Under ₹1L and about two months to a working loop with real numbers.

---

## Version C — component ledger

| Component | Solo? | Notes |
|---|---|---|
| Verified-spot pipeline | ✅ Via B | B *is* this component. |
| Unit-economics model | ✅ Fully | From your own Porter runs + kit costs: staging time, delivery cost, ₹ per person served. CSR decisions run on exactly this number, and yours will be measured, not estimated. |
| Rider-as-sensor experiment | ✅ Informal | The single most persuasive C artifact, and it needs no platform: spend evenings at dark-store/pickup clusters in your zone, recruit 10–30 friendly riders into a WhatsApp group, ask them to drop a pin when they pass someone in need. Measure flags/week and verified-rate. Keep it off-platform, voluntary, unbranded (don't use platform names/logos), and don't pay per report (that buys junk). "31 riders sent 214 flags in six weeks; 58% verified" turns the in-app-flag feature from your speculation into their obvious next step. |
| Depot staging simulation | ✅ Fully | A shelf at home is the dark store: measure pick-pack-dispatch time per aid drop. Boring, and exactly what their ops team will ask. |
| Draft MoU + data-governance spec | ✅ Fully | Write the platform-never-sees-subject-data architecture, the rider opt-in/training outline, and the gig-law notice plan *before* the meeting, so "how would this work legally?" is a handout, not a follow-up. |
| ₹5 checkout-donation rail | ❌ Platform-only | No honest solo proxy — and don't run public fundraising without an entity. Its *evidence* is Feeding India's existing rail (200K meals/day), which you cite, not build. |
| Official in-app rider flag | ❌ Platform-only | Your informal experiment is its business case. |
| "Aid Drop" order type, training, pay, no-rating-penalty | ❌ Platform-only | Requires their app, their contracts, their gig-law filings. |
| CSR funding + ESG reporting loop | ❌ Platform-only | Your metrics spine is what makes it auditable — that's your seat at the table. |

**What C looks like on pitch day if you do the solo work:** you walk in with a live product (hand the CSR lead your QR mid-meeting and let them watch their own report get verified), six months of loop metrics, a rider-sensor experiment with conversion rates, measured unit economics, a drafted MoU — and a Goonj relationship. At that point you're not asking them to believe anything; you're asking them to plug four things they already own into a machine that demonstrably runs.

---

## Pitch sequencing (latest responsible moment for each)

1. **Week 5–8 — outreach/street-medicine NGO** (forced by wound cases; low-stakes; brings clinical legitimacy and field capacity).
2. **Month 3–5 — Goonj** (optional accelerator: kit assembly at scale, dignity framing, credibility halo; go with distribution data showing what people actually accepted).
3. **Month 4–6 — entity registration** (trust/Section 8 + 80G path) once continuing is certain — prerequisite for public donations and MoUs, not for operating.
4. **Month 6+ — platform** (Feeding India's partner door or Blinkit's ambulance/CSR team), carrying the pitch pack above. This is the only high-stakes pitch in the sequence, and by design it happens last.

## Solo-phase guardrails (non-negotiable)

Daylight only; public places; tell someone where you are, better yet bring a friend; never perform wound care — refer and log; ask before giving and accept refusal gracefully; no uniform, lanyard, or anything implying authority; consented photos only, deleted after case close; and the privacy architecture (no names, expiring pins, aggregate-only analytics) applies from report #1 — solo scale is not an excuse to build the dangerous database.

## Bottom line

Independence favors B overwhelmingly: **~75% of B is buildable and operable alone for under ₹1L**, and the missing 25% (clinical care, scale, entity) only becomes necessary once the working loop has earned partners' attention. **C is ~30% buildable but ~80% de-riskable solo** — and every simulation lives inside B's daily operation. So "how far can I get independently?" has a concrete answer: *to a functioning product with proprietary data that nobody else in India has* — which is much further than most funded teams get before their first partnership meeting.
