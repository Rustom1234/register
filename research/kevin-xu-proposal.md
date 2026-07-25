# Pukaar — proposal for the Kevin Xu Innovation Challenge

> **Status:** submission draft. Items in [square brackets] need your personal details before submitting. Built for the challenge's known shape (up to £25,000 non-dilutive; application → semi-finalist workshops on problem definition, experiment design, business case → live pitch at the Rhodes Forum). Confirm the 2026 theme and dates with Equitech when applications open.

---

**Project:** Pukaar (Hindi: "the call") — working title
**One-liner:** A witness-powered aid network for people on India's streets: anyone who sees someone in need sends a 90-second WhatsApp report; a verified outreach worker responds with a dignity-designed aid kit and a medical escalation path — with AI working on *reports, never on people*.
**Applicant:** Rustom Dubash, Equitech Futures alum [cohort/program, 1 line]
**Ask:** £24,000 over 12 months | **Location:** Delhi, India (zone 1 + winter expansion)
**Partners (in progress):** Goonj (kit assembly, material supply — personal connection, pitch scheduled); one street-medicine/outreach NGO (clinical escalation) [name when confirmed]

---

## 1. Executive summary

Last month I walked past a homeless man whose wrapped foot was bleeding through the bandage. ₹200 of antiseptic, fresh dressings, and a raincoat would have changed his week. Nobody stopped — not because nobody cared, but because there was nothing to plug that moment of caring into.

Pukaar is that plug: a WhatsApp reporting line, a human verification layer run with outreach NGOs, a ~₹300 aid kit co-produced with Goonj from urban surplus material, and a logged outcome for every case — including escalation to street-medicine care when a kit isn't enough. Our research (65+ sources, July 2026) found that **no system anywhere closes this loop**: reporting apps exist (StreetLink, UK), charitable delivery rails exist (DoorDash Project DASH), NGO kit engines exist (Goonj), street medicine exists — but nobody connects witness → verification → material aid → care. India is the right place to connect them: the world's densest delivery fleets, an in-app micro-donation culture that already funds 200,000 meals/day, and a proven citizen-report-to-dispatch pattern (Delhi's Rain Basera, No Food Waste's hunger spots).

AI's role is deliberately inverted from the surveillance default: no cameras, no biometrics, no database of the poor. AI works on *witness reports* — triage, deduplication, hotspot forecasting for outreach routing — augmenting the judgment of reporters, riders, and outreach workers. Pukaar treats India's 7.7M gig workers not as jobs to automate but as the country's largest humanitarian sensor network, opted-in one tap at a time.

## 2. The problem

India's official count of homeless people is 1.77 million (Census 2011); activists hold the real figure to be a multiple of that. They are disproportionately invisible to formal systems — unaddressed, often phoneless, and in ~20 states still subject to criminal begging laws. The consequences are most acute at the level Pukaar targets: untreated wounds, exposure in monsoon and winter (Delhi NGOs have counted hundreds of cold-linked deaths in a single winter), and minor conditions that become emergencies for want of ₹200 of supplies and one clinical look.

The failure is not compassion or capacity — passersby care, outreach teams exist, material surplus exists. The failure is **connective**: the moment of witnessing and the machinery of response are not wired together. The UK's StreetLink proves both halves of this: 170,000+ citizens filed reports (demand for witness action is real), but outreach found the person only 23% of the time and only ~5% reached housing (unverified, slow loops squander that demand). The loop — fast verification, material response, logged outcome — is the missing infrastructure.

## 3. What we learned before designing this (evidence base)

We ran a four-track research sweep (detection technology; delivery/CSR rails; open source and apps; law and ethics) before committing to this design. Five findings shaped it:

1. **Camera-based detection of need is a dead end** — technically (San Jose's pilot: 97% accuracy on potholes, 10–15% on "is someone living in this car"; component shut down in 2025 over privacy), legally (India's DPDP Act offers no consent basis; feeds are police-controlled), and morally (Indore's CCTV-monitored "beggar-free" drive files FIRs against people *giving* alms — location data about the poor has a documented enforcement afterlife in India). Pukaar is architected so the dangerous database **never exists**.
2. **Human reporting works and is already Indian practice**: Delhi's DUSIB runs a photo→GPS→rescue-van app and helpline (14461); No Food Waste's citizen-pinned "hunger spots" (verify → deliver food to the spot) has fed 285,000+ people. Pukaar generalizes this proven pattern from food to aid + medical escalation.
3. **The paid-delivery rail for aid is proven** (Project DASH: 8M+ deliveries, riders paid normal rates) and Indian quick-commerce has demonstrated appetite for street-level health logistics (Blinkit: 25 ambulances in NCR within a year).
4. **Follow-through is where these systems die** (StreetLink's 23% found-rate). Pukaar's core metrics are found-rate, time-to-verify, and cost per verified need served — not report counts.
5. **Nothing like the full loop exists** — no product, government program, or open-source project connects witness reports to verified material aid anywhere. (Full landscape with ~70 sources in the project repository.)

## 4. The solution

**Report (90 seconds).** Anyone — passerby, security guard, delivery rider — messages a WhatsApp number: location pin, one-tap category (injury/wound · rain-cold protection · hunger · shelter), optional photo. Emergencies are redirected to 112 immediately. No app install; works on any phone that has WhatsApp, which in urban India is effectively every phone.

**Verify (same day).** Reports land in a dashboard for the zone's outreach partner. Duplicates auto-merge; unverified reports expire in 72 hours. A trained outreach worker — not the reporter, not a gig rider — goes to the person, talks with them, and decides what's needed. Wound and illness categories simultaneously alert the partner's clinical team: **a kit must never substitute for care.**

**Respond (with dignity).** The worker carries Pukaar kits: wound-care basics (all OTC), ORS, soap, socks, seasonal protection (raincoat/tarp or blanket), and an information card for shelters, helplines, and the mobile medical van schedule — packed in a cloth bag sewn from Goonj surplus. Kits are co-designed with Goonj and with people who have lived street experience, honoring Goonj's founding principle that the receiver is a stakeholder, not a beneficiary.

**Close the loop.** Every case ends in a logged outcome: found / not found, accepted / declined, escalated / completed. The reporter gets one message — *"An outreach worker reached the person you reported. Thank you for stopping."* — which converts single reporters into repeat ones. Monthly *aggregate* heatmaps (never live, never granular) go to outreach partners and, eventually, city shelter planners.

**Privacy by architecture (non-negotiable design):** no names or identifiers of street residents; photos deleted at case close; pins expire; analytics on coarse area cells only; reporter numbers hashed; no data sharing with enforcement, ever, contractually. In a country where begging is still widely criminalized, the strongest privacy guarantee is that the sensitive dataset is never created.

## 5. Where AI fits — and where it refuses to

The challenge asks how AI can empower rather than threaten. Pukaar's answer is an inversion: in this domain the "obvious" AI (cameras scanning streets for the poor) is the threatening kind — so Pukaar puts AI on the *reports*, in service of the humans in the loop:

- **Triage and prioritization** of incoming reports (urgency, freshness, category confidence — precedent: DSSG × Homeless Link's ML on StreetLink reports), so verification capacity goes where it matters first.
- **Deduplication and case-linking** across reports and revisits, so three witnesses of one man become one case, not three dispatches.
- **Photo-assist at verification** (assistive classification of report photos for the *queue*, human decides everything downstream).
- **Hotspot forecasting** on aggregate cells to route outreach rounds and pre-position winter stock — the SDSU-San Diego model of AI-for-outreach-routing, minus the aerial surveillance.
- **A refusal, stated in the application:** no facial recognition, no biometric categorization, no CCTV inference, no individual risk-scoring of street residents. This is an AI-ethics position with teeth, derived from documented harms.

The livelihood angle runs deeper than ethics hygiene: phase 2 invites delivery riders to become opt-in humanitarian sensors (a one-tap flag), and the eventual platform program ("Aid Drops") creates *paid* charitable delivery work at standard rates — AI-era infrastructure that adds meaning and income to gig work rather than extracting from it.

## 6. Differentiation

The 2025 challenge winner, OpenDoor, builds infrastructure connecting people experiencing housing insecurity with existing social services — validation that this problem space matters to the challenge. Pukaar is complementary and distinct on four axes: it activates **witnesses** (the supply of compassion on every street) rather than navigating services for the person directly; it moves **physical material** (kits, via an NGO production chain) not only referrals; it runs **India-first** under Global-South constraints (phoneless recipients, criminalization risk, DPDP, no address layer); and its AI is **report-side by explicit anti-surveillance design**. No existing project — commercial, governmental, or open source — occupies this position (evidence: §3.5).

## 7. Pilot design (the experiment)

**Setting:** one ~3 km² Delhi zone (months 1–6), expanding to a second zone for winter (months 7–12). Delhi chosen for Goonj HQ, existing street-medicine activity, and DUSIB's complementary shelter-rescue system.

**Primary outcome:** cost per verified need served (target ≤ £8 all-in by month 12).
**Secondary outcomes:** found-rate (target ≥50% vs StreetLink's 23% benchmark); acceptance rate (≥60% — a dignity gauge, not just an ops gauge); median report→verification time (≤24h); clinical escalations completed (≥300); repeat-reporter rate (≥30%).
**Experiments embedded:** A/B of report-seeding channels (chemist QR posters vs RWA groups vs guard/driver networks) on volume and precision; kit content iteration from refusal/request logs; rider-sensor sub-study (months 7–12): 30 opt-in riders, flags/week and verified-rate vs citizen reports.
**Kill criteria (pre-registered):** verified-need rate <40%; acceptance <50%; cost per verified need >3× kit cost; partner backlog growing 4 weeks straight. We commit to publishing results either way — a negative result on witness-report precision in an Indian megacity is itself a contribution the field lacks.

## 8. Twelve-month plan

- **M1–2** — Kit v1 workshop (Goonj + clinical partner + lived-experience advisors); 500 kits assembled; bot + dashboard live; entity registration begun; zone seeded.
- **M3–6** — Zone 1 live. Weekly ops rhythm; monthly metric reviews against kill criteria. Mid-point: ~600 kits deployed.
- **M7–8** — Winter surge: zone 2, blanket-heavy winter kits (Goonj's Odha Do Zindagi stock), DUSIB coordination so Pukaar reports can also route people to shelter beds.
- **M9–11** — Rider-sensor sub-study; 2,500 cumulative kits; platform conversations begin *with data* (Feeding India partner channel / Blinkit CSR), MoU and data-governance drafts ready.
- **M11–12** — Independent evaluation; public report + open-source release of the playbook (bot flows, dashboard, kit spec, privacy architecture) so other cities can replicate.

## 9. Budget (£24,000 · ≈ ₹25 lakh · founder time pro bono)

| Line | £ |
|---|---|
| Program coordinator, Delhi, 12 months | 4,000 |
| Outreach partner field-capacity grant (verification & response hours) | 3,500 |
| 2,500 aid kits @ ~₹300 with Goonj | 7,000 |
| Dispatch & courier (restock rail + urgent runs) | 1,200 |
| Tech: WhatsApp BSP fees, hosting, dashboard | 1,000 |
| Legal: Section 8 entity, DPDP compliance review, partner MoUs | 1,500 |
| Dignity design & training (lived-experience advisors, worker/rider modules) | 900 |
| Independent evaluation | 1,500 |
| Zone seeding & community materials | 800 |
| Field ops & travel | 700 |
| Contingency (~8%) | 1,900 |
| **Total** | **24,000** |

## 10. Team & fit

[Rustom Dubash — 2–3 lines: Equitech program/cohort, technical background, current role/city.] Founder-led fieldwork is the point: the design phase (completed) included a full landscape and legal review, and the pilot begins with the founder personally running verification — the fastest route to honest data. **Goonj** relationship is personal [1 line on the link]; Goonj brings 25 years of surplus-to-aid logistics and the dignity ethos this design is built around. Clinical escalation via a Delhi street-medicine/outreach partner [shortlist: mobile-health-van NGOs active in Delhi; name at submission]. Advisors sought through the challenge's mentorship: AI-ethics reviewer, humanitarian-logistics mentor.

## 11. Risks and honesty

The three ways this most plausibly fails, and the design answer: **(1) Report noise/low precision** — tight zone, photo + freshness prompts, pre-registered 40% kill line. **(2) Verification capacity** — partner-capacity grant in the budget; we never generate more verified need than the partner can serve; backlog is a kill metric, not an inconvenience. **(3) Data misuse pressure** (police/municipal requests, partner Aadhaar-linkage demands) — the data that could be demanded is never collected; MoUs bar enforcement sharing; we accept losing a partnership over this. Broader register of legal/ethical analysis (DPDP, SaMD boundary, Good Samaritan scope, gig-worker law) is in the project repository.

## 12. After the grant

The pilot's numbers are the key that unlocks sustainable funding: India's platforms already run the exact financing rail Pukaar needs (₹1–10 checkout donations fund 200,000 meals/day) and have proven street-level humanitarian appetite. Phase C ("Aid Drops") pitches one platform to make aid kits a checkout donation option and a normally-paid, opt-in delivery type — with Pukaar as the verification and outcomes layer platforms cannot credibly build themselves. Goonj's national footprint (23 states) and the playbook's open-source release define the replication path; the loop, once proven in Delhi, is a pattern, not a place.

---

*Appendix (project repository): landscape research with ~70 sources · critique & scoping · plan deep-dives · solo-buildability analysis · this proposal.*
