# Deep-research prompt: "Street Aid" concept validation

Copy everything below the line into Claude with web search / Research mode enabled. Fill in the two `[...]` placeholders first if you can (city, budget); leaving them generic also works.

---

You are a skeptical product-research analyst with domain expertise in civic tech, humanitarian logistics, computer vision, and Indian regulation. Your job is to validate — or kill — a product concept using current evidence (prioritize 2023–2026 sources). Do not be agreeable. Where the evidence is against me, say so plainly and argue for the strongest alternative instead.

## The concept (steelman it first, then attack it)

Trigger story: I walked past a homeless man with an injured foot — wrapped, bleeding through the bandage. Roughly ₹200 of antiseptic, fresh dressings, and an umbrella would have materially changed his week. Nobody stopped, including me, and I want to build the thing that makes stopping unnecessary.

Proposed system, India-first:

1. **Detect** — use existing street/traffic camera imagery (speed cameras, ANPR, smart-city CCTV) plus computer vision to flag people who visibly need basic medical supplies or weather protection.
2. **Fulfil** — route a standardized "street aid kit" to that location through hyperlocal delivery fleets (Zomato, Blinkit, Swiggy Instamart, Uber Eats): for example, roughly one in every N deliveries a rider does becomes a funded "giving run".
3. **Fund/Supply** — platform CSR budgets and/or nonprofits pay for the kits. I have a personal connection to Goonj (the Indian NGO that converts urban surplus material into aid, with a dignity-first ethos) as a possible supply and distribution partner.

I am open to radically reshaping any of the three layers — detection especially — if the evidence says so.

## Research questions

### A. Prior art — detection
1. Has anyone used street/CCTV/traffic cameras plus AI to detect homeless people or people in distress? Known lead: San Jose, California ran an encampment-detection pilot around 2024 — find its current status and public reception. Any smart-city equivalents in India or elsewhere? Do commercial video-analytics products ship "fallen person / person down" detection?
2. Has anyone anywhere attempted to infer *need for medical supplies or wound care* from street imagery? If you find nothing after genuinely searching, state that absence explicitly — it is a key finding.
3. What do Indian traffic-enforcement cameras actually capture (what they are aimed at, resolution, sidewalk coverage)? Who operates them (state police, municipal ICCCs, private vendors)? Is there any precedent of a third party or startup getting access to feeds? What does the Smart Cities Mission ICCC data-sharing policy actually allow?

### B. Prior art — fulfilment and funding rails
4. Charitable-delivery programs that run on gig fleets: DoorDash Project DASH, Uber's programs, Zomato Feeding India, Swiggy's NGO partnerships (e.g., Robin Hood Army), Blinkit's 10-minute ambulance service — for each: how it works, who pays the rider, and its current status.
5. Has any platform delivered goods to an unaddressed GPS pin or directly to a person on the street? How do NGOs solve the "no address" problem (Google plus codes, what3words, the "Addressing the Unaddressed" project)?
6. How are such programs funded, and what is the evidence on CSR-funding durability over multiple years?

### C. Prior art — the human-reporting alternative
7. Citizen-reporting systems: StreetLink (England/Wales), Samaritan (Seattle), Miracle Messages, Delhi's DUSIB winter-rescue helpline and vans, and anything similar in Indian metros — mechanics, scale, measured outcomes, and known failure modes.
8. Street medicine and wound-care outreach for homeless populations (Street Medicine Institute globally; mobile medical units in Indian cities) — who already does the medical part, and what do they say they lack?
9. Open-source, GitHub, or hackathon projects in this space — is anything beyond toy quality?

### D. Law and ethics (India-first)
10. DPDP Act 2023 applied to: processing CCTV images of identifiable people, inferring a person's health condition from images, and targeting individuals with services based on that inference. Where are the hard stops, and what is the enforcement status of the rules as of now?
11. The surveillance-of-unhoused-people critique: what was the reaction when cities tried this (San Jose), are there documented cases of "helpful" homelessness data being reused for sweeps or enforcement, and how do India's begging-criminalization laws (e.g., Bombay Prevention of Begging Act; Delhi HC 2018 ruling) change the risk that my data endangers the people I want to help?
12. When does software that flags "this person needs medical attention/supplies" become regulated triage or medical-device software (India CDSCO software-as-medical-device guidance; FDA clinical-decision-support rules; EU AI Act high-risk categories as context)? What is the liability picture if a flagged person receives a kit instead of care and deteriorates? Does India's Good Samaritan framework (2016 guidelines, MV Act §134A) protect organized aid delivery or only bystanders?
13. Gig-worker law and economics: Rajasthan's 2023 platform gig workers act, Karnataka's legislation, and platform obligations generally. What constrains routing riders to charitable tasks? Compare my "1-in-5 deliveries" mechanic against paying riders normal per-drop rates from a CSR budget (the Project DASH model) on rider earnings, consent, and platform incentives.

### E. Synthesis
14. **Verdict**: does an end-to-end camera→detect→deliver system exist anywhere? What, precisely, is novel in my concept — and what parts are commodity?
15. **Red team**: the top 10 ways this fails, ranked by lethality. Ground each in a cited source or a named first-principles reason (physics of camera resolution, unit economics, refusal rates — not vibes).
16. **Pivots**: at least 3 alternative shapes that keep the goal — fast, dignified, funded material aid to people on the street — while fixing the worst flaws. Consider at minimum: (a) delivery riders as opt-in human sensors (a one-tap "person needs help here" flag in a rider-facing tool instead of cameras); (b) WhatsApp-first citizen reporting with NGO verification before fulfilment; (c) routing and supply tooling for existing outreach systems (DUSIB rescue vans, street-medicine teams, Goonj's material flows). Score each pivot on impact, feasibility, ethics, cost, and fit with Goonj.
17. **Recommendation**: ONE 90-day MVP for [CITY — default Delhi], budget under [BUDGET — default ₹5 lakh]: scope, which partners to approach in what order, 3–5 success metrics, and explicit kill criteria.

## Output format
- Start with a landscape table: solution | what it does | geography | status (production / pilot / dead) | overlap with my idea | gap it leaves.
- Then sections D and E as prose with headers.
- Cite every load-bearing claim with a dated source. Prefer primary sources. Mark anything you could not verify. Distinguish "searched and found nothing" from "did not search".
- End with the 5 most important open questions I should answer next — and for each, the cheapest way to answer it (a phone call, an RTI request, a site visit — not more desk research).

## Standards
- India-first; global evidence welcome as precedent.
- Recency matters: flag anything that changed after 2024.
- No sycophancy. If the camera layer deserves to die, kill it and tell me what survives.
