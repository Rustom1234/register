# Wayside — outreach & implementation plan (India + Nepal)

*Compiled 2026-08-10. Purpose: turn a working demo into a real pilot with
real people. This document is the target list, the sequence, and the
scripts.*

> **READ THIS FIRST — how to treat the contact details in this document.**
> Every contact below was gathered by automated web research and is
> tagged `[OFFICIAL SITE]` (fetched from the organisation's own domain) or
> `[THIRD-PARTY]` (a directory, registry or news article — frequently
> stale). **Nothing here has been dialled or emailed to confirm it.**
> NGO websites in India and Nepal go stale fast, staff move, and grant
> deadlines shift every cycle. Before you send anything: open the source
> URL, confirm the address still exists on the live page, and confirm the
> person is still in post. Treat a `[THIRD-PARTY]` contact as a lead, not
> a fact. Where research could not find a detail it says **not found** —
> that is deliberate, and it is never to be filled in by guessing at a
> pattern like `firstname@org.org`.

---

## 0. What you are actually asking for

Everything in this plan reduces to one of four asks. Know which one you
are making before you open your mouth, because they have different
answers and different decision-makers.

| # | The ask | Who grants it | What it unlocks |
|---|---|---|---|
| **A** | **Be my pilot partner.** 2–5 outreach workers, a shelf for ~30 kits, 8–12 weeks, one neighbourhood. | An NGO's programme head or founder | The only thing that turns a demo into evidence |
| **B** | **Fund the kits.** ~₹35,000 one-time + ~₹4,000/month. | A CSR desk, a small foundation, a student prize | Removes the excuse that the NGO has no budget |
| **C** | **Lend me your riders or your shelf space.** | A quick-commerce / delivery company | Solves the depot and last-mile problem at zero marginal cost |
| **D** | **Tell me why this is wrong.** | Academics, practitioners, prior-art operators | Stops you burning a year on a known dead end |

**The ordering matters.** A is the bottleneck. B, C and D are easier to
get and are worth much less without A. Do not spend August chasing money
you cannot deploy.

---

## 1. The pilot offer — one page, memorised

This is what you are proposing to an NGO. It has to be small enough to
say yes to without a board meeting.

**What Wayside is:** anyone who sees a person in need on the street sends
one WhatsApp message and a pin. The report is structured automatically in
whatever language they wrote it in. Genuine emergencies are caught by a
fixed 112 gate — no AI ever speaks in that path. Everything else becomes
a kit order dispatched to *your* outreach worker, who collects a
pre-stocked kit from *your* office and delivers it. The person who
reported is told how it ended.

**What you are asking the NGO for:**
- 2–5 outreach workers who already walk that neighbourhood, with Android
  phones they already own
- One shelf, in premises they already have, for ~30 kits
- 8–12 weeks
- One person who owns outcomes and safeguarding

**What you provide, at no cost to them:**
- The whole system, running, free — hosting is ~₹450–1,300/month and you
  cover it
- The initial kit stock (~100 kits, ~₹30,000) *if* you land ask B first
- Training, and you personally on call for the pilot
- A public results page, including the failures

**What they get:** a channel through which the public routes work to
them, with an audit trail; evidence for their own funders; and no
new database of the poor to defend — 72-hour case expiry, pins deleted,
only coarse 90-day aggregates survive.

**The pre-registered kill line.** If Wayside cannot serve a person for
under ₹900 all-in, its own dashboard says so, you publish it, and you
stop. Say this *unprompted* in the first meeting. It is the single most
credible thing you have, and NGOs have been burned by tech volunteers who
would not name a failure condition.

**Numbers you may quote** (all sourced in `kit-costs.md` and
`cost-breakdown.md`): kits at ₹172 medical / ₹50 food / ₹173 monsoon
wholesale; ~₹430 all-in per person served; ~₹35,000 one-time and
~₹3,000–4,000/month to run an 8-week single-zone pilot; 245 automated
tests; real OpenStreetMap routing over 1,432 surveyed road segments.

---

## 2. Sequence — what to do, in order

**Weeks 1–2 · Make it real to look at.**
Wayside is currently a link that takes 22 seconds to wake up and shows an
invented city on the live deployment. Before you send a single email:
point the deploy at the branch with the real map, set up a `/health`
pinger so it is warm, and put the 1:45 demo film somewhere with a stable
URL. An NGO director clicking a dead link is a lead you do not get back.

**Weeks 1–2 · Ask D, in parallel, because it is free.**
Email the prior-art operators and the academics. You are asking for 20
minutes and a critique, not money. Two purposes: you will learn whether
someone already tried this and why it failed, and a named advisor makes
ask A dramatically easier.

**Weeks 2–5 · Ask A, hard, in Delhi only.**
Twelve to fifteen NGOs, personally, in order of the shortlist. Do not
mass-mail. Do not start in Nepal — you cannot be on the ground there, and
a pilot you cannot physically attend will fail in a way that teaches you
nothing.

**Weeks 3–8 · Ask B, timed to the deadlines that exist.**
Rolling funders can be applied to at any time and should be done in week
3. Fixed-deadline prizes get slotted where they fall.

**Weeks 6+ · Ask C, but only with A in hand.**
A quick-commerce CSR desk will not engage with an idea. It will engage
with "we run in Nizamuddin with [NGO], here is the data, we want a shelf
in your dark store." Going early wastes your one shot.

**Nepal: not before month 4.** See §8.

---

## 3. Outreach scripts

Short, specific, and asking for a small thing. All three are written to
be sent as-is after you fill the brackets.

### 3a · NGO first contact (ask A)

> **Subject:** 20 minutes — a way for the public to send you street cases in [AREA]
>
> Dear [NAME],
>
> I built a system that lets any passer-by who sees someone in need on the
> street in [AREA] report it in one WhatsApp message with a pin — and puts
> that case straight into the hands of an outreach worker with the right
> kit. It routes on the real streets of [AREA] and it is working today:
> [DEMO LINK] (1 minute 45).
>
> I am looking for one partner organisation to run an 8-week pilot. What I
> would need from you is small: 2–5 of your outreach workers using the
> phones they already have, a shelf for about 30 kits, and someone who
> owns outcomes. I cover the technology and I am on call throughout. I am
> not asking you for money.
>
> I have also pre-registered a condition for failure: if this cannot serve
> a person for under ₹900 all-in, my own dashboard says so, I publish it,
> and I stop.
>
> Could I have 20 minutes — at your office, whenever suits?
>
> [NAME] · [PHONE] · [EMAIL]

**Why it is shaped like this:** it leads with what *they* get, the ask is
concrete and small, the failure condition is stated before they have to
ask, and it requests a meeting rather than a decision.

### 3b · Corporate CSR / partnerships (ask C)

> **Subject:** Nizamuddin street-aid pilot — a shelf in one dark store
>
> Dear [NAME],
>
> I run Wayside, a witness-powered street-aid service piloting in
> Nizamuddin with [NGO PARTNER]. When someone sees a person in need on the
> street, they send one WhatsApp message; a trained outreach worker
> collects a kit and delivers it. [ONE LINE OF PILOT RESULTS.]
>
> One thing would materially change our reach: shelf space for 30 kits in
> a single [COMPANY] dark store in South-East Delhi. No cash, no
> integration, no rider time — just a shelf in a location you already
> operate, close to where the need is.
>
> If that is interesting I can send our one-pager and the pilot data.
>
> [NAME] · [PHONE]

**Do not send this without pilot results in the second paragraph.**

### 3c · Advisor / prior-art request (ask D)

> **Subject:** Your work on [SPECIFIC THING] — a question about a street-aid dispatch tool
>
> Dear [NAME],
>
> I am a student who has built a witness-powered street-aid dispatch
> system for Delhi — the public reports someone in need, an NGO outreach
> worker is dispatched with a kit. Before I put it in front of any NGO I
> want to understand what has already been tried and what went wrong.
>
> You have written about / run [SPECIFIC THING]. My specific question is:
> [ONE PRECISE QUESTION].
>
> I am not asking for funding or an endorsement — 20 minutes of scepticism
> would be worth more.
>
> [NAME]

---

## 4. The hard questions you will be asked

Have an answer to each before your first meeting. These are the ones that
kill pitches like this.

**"Who asked the person on the street if they wanted to be reported?"**
Nobody, and that is the real ethical weight of this design. The honest
answer: the report is about a *need*, not an identity; no photo of a face
is required; the record expires in 72 hours; the pin is deleted; nothing
that could become a map of where vulnerable people sleep survives past 90
days, only coarse cell counts. The person is never named, never
registered, and never enrolled in anything. But say plainly that the
consent problem is real and unsolved in the general case.

**"Isn't this surveillance of the poor?"** The strongest version of this
critique is in the academic literature on automated welfare systems
(see §7 research). Wayside's answer is architectural — there is no
database of people, only short-lived cases — but you should be able to
state the critique better than the person asking.

**"What happens if a witness reports a medical emergency?"** A fixed
regex gate catches it before any model runs and returns a fixed 112
message. No AI ever speaks in the emergency path. This is tested at 100%
recall on the test corpus.

**"Why won't this just create work we cannot meet?"** Because the wave
system stops: an order that no one accepts goes to a human coordinator
rather than into a void, and the witness is told honestly. And because
you can turn the intake off by neighbourhood.

**"You are a student. What happens when you go back to school?"** Answer
honestly. This is the question that most often ends these conversations,
and a vague answer is worse than a limited one.

---

## 5. Delhi / NCR NGOs — ask A

*Populated from research. See the sourcing warning at the top.*

Twenty-two organisations were researched. These are the ones that matter,
ranked for a Nizamuddin pilot. **Verification status is mine, not the
researcher's:** I re-fetched the top three myself — SPYM's details
confirmed live on their own site; Hope Project and CHD returned HTTP 406
to an automated request, which means blocked, not wrong.

### The five to approach first

**1 · Hope Project (Nizamuddin) — the local anchor.** Fifty years inside
Basti Hazrat Nizamuddin, health and education programmes, trusted by the
neighbourhood. They are *in the pilot zone*; nobody else on this list is.
Community trust here is the thing you cannot build yourself, and their
office is a natural depot.
- Web: hopeprojectindia.in · Email: info@hopeprojectindia.in ·
  Phone: +91 7303501350 · 127 Basti Hazrat Nizamuddin, New Delhi 110013
- Named: Samiur Rahman, Executive Director (publicly listed)
- `[OFFICIAL SITE]` per research; **my re-fetch got 406 — confirm by phone first**
- Caveat: they are a community-development body, not a street-rescue
  outfit. They may not have outreach workers who walk at night.

**2 · SPYM — operational scale.** The largest shelter operator in Delhi,
a DUSIB contract-holder, running dozens of shelters including Lodhi Road
and Sarai Kale Khan — both minutes from the zone. Their Homeless
Intervention Programme is close to Wayside's model already.
- Web: spym.org · Email: info@spym.org · Phone: 011-41003872 ·
  SPYM Centre, 111/9 Vasant Kunj, New Delhi 110070
- **Verified by me on 2026-08-10** — email and phone both live on spym.org
- This is the one that could absorb a pilot without strain.

**3 · Centre for Holistic Development (CHD) — night outreach.** Runs
twice-weekly night vigils for homeless people; rights-based; South Delhi
base adjacent to the zone. The closest existing practice to what Wayside
dispatches.
- Web: chdindia.org.in · Email: info@chdindia.org.in ·
  Phone: 011-41084099 / +91 9811327037 · 1D First Floor, Shahpur Jat,
  New Delhi 110049 · Named: Sunil Kumar Aledia
- `[OFFICIAL SITE]` per research; my re-fetch got 406 — confirm before sending

**4 · Aashray Adhikar Abhiyan (AAA) — the homelessness specialists.**
Adult street homelessness specifically, with outreach teams and shelters.
Founded by Sanjay Kumar, who was himself homeless for twelve years — if
anyone will tell you honestly whether this idea is patronising, it is
this organisation.
- Web: homelesspeople.in · Email: righttoshelter@hotmail.com ·
  Phone: 011-22022440 · Helplines 9312668807 / 9810711644
- Note the hotmail address — verify it is still monitored before relying on it.

**5 · Prayas JAC Society — safeguarding and training.** Founded by a
former Delhi DCP, large footprint, real safeguarding systems. Best used
for responder training and child-case protocols rather than as the lead.
- Web: prayaschildren.org · Email: prayas@prayaschildren.org ·
  Phone: 011-29955505 · Named: Amod Kanth, Founder

### Others worth knowing

| Organisation | Why | Contact | Note |
|---|---|---|---|
| Aga Khan Trust for Culture — Nizamuddin Urban Renewal | Runs the Sunder Nursery / Basti programme in the exact zone; community credibility | Phone +91-11-43717792; web nizamuddinrenewal.org | Email on site is an anti-scraping placeholder — **not found**. Named: Ratish Nanda, Project Director |
| Prerna (Social Dev. & Welfare Society) | DUSIB shelter operator, Adhchini (South Delhi) | info@prerna.org · 011-40193719 | Good secondary depot |
| Sadik Masih Medical Social Servant Society | ~15 Delhi shelters, 24/7 | info@sadikmasihindia.org.in · +91-98110-25437 | 24/7 matters for night cases |
| CHETNA | Street children, trained outreach workers | info@chetnango.org · 011-41644471 | Child cases |
| Salaam Baalak Trust | Street children, Paharganj | contact@salaambaalaktrust.org | Cross-referral, not lead |
| Centre for Equity Studies (Harsh Mander) | Street medicine + the intellectual case for dignity | centreforequitystudies.org | Approach as advisor (ask D), not partner |
| Childline 1098 | Child emergency referral | 1098 helpline | Your child-case escape hatch. Know the number before you launch |
| Uday Foundation | Runs kit distribution already — blankets, hygiene, food | 011-41098444 | Email on site is a placeholder — **not found**. Talk to them about kit sourcing |
| Urban Health Resource Centre | Street-medicine research, kit design | uhrc.in — **site was down (503)** | Medical kit contents |
| Chetanalaya | Catholic diocesan social work, wide network | No contact found on site | Referral partner at best |
| Goonj | Material redistribution at national scale | 011-41401216 `[THIRD-PARTY]` | Email is a placeholder — **not found**. Kit materials, not outreach |
| Robin Hood Army | 50k+ volunteers, WhatsApp-native, deliberately app-free | WhatsApp +91-89719-66164 `[THIRD-PARTY]` | See §11 — their anti-app stance is a design lesson, and they are an ally not a partner |
| Sulabh International | Sanitation, slum presence | contact@sulabhinternational.org · 011-25031518 | Peripheral |
| Aman Biradari | Harsh Mander-linked | Third-party contact only, low confidence | Verify existence before writing |
| Don Bosco Ashalayam | Child residential care | No contact on official pages | Needs a phone call |
| YUVA (Delhi Police) | Police youth programme | 011-23473959 | Only if you decide police contact is desirable — think hard first |

---

## 6. India — national NGOs, other metros, and networks

Twenty-five organisations researched. Delhi is covered in §5; this is
everything else. **None of these are for now** — they are the month-4+
list, once a Delhi pilot has produced evidence.

### Strongest street-outreach candidates outside Delhi

| Organisation | City | Why they fit | Contact |
|---|---|---|---|
| **Pehchan Foundation** | Mumbai | Homeless-rights work with an actual **homeless helpline** already running (+91 8108975975) — the closest thing to Wayside's intake in India | pehchan.mumbai@gmail.com · +91 9869669392 |
| **BOSCO** | Bengaluru | 35 years, six outreach hubs across the city, round-the-clock street presence | boscoban@gmail.com · +91 8197569172 |
| **Hope Foundation Kolkata** | Kolkata | Emergency response teams, healthcare integration, large reach | info@hkf.ind.in · +91-33-2474 2904 |
| **Karunalaya** | Chennai | 25+ years with pavement-dwelling communities | karunalaya@gmail.com · +91 94458 71098 |
| **APSA** | Bengaluru + Hyderabad | Street children, two-city footprint | projects@apsabangalore.org · 080-25232749 |
| **CCDT** | Mumbai | Community health with vulnerable urban families | contact@ccdtrust.org · 8657898537 |
| **Snehasadan** | Mumbai | Street-children homes, long history | snesadan@yahoo.com · +91 83558 97568 |
| **Shelter Associates** | Pune | Urban poor housing, data-literate — they will understand the privacy design | info@shelter-associates.org · +91 8087607545 |
| **Doctors For You** | National | Medical response; relevant to the MED kit and clinical escalation | info@doctorsforyou.org · +91 7388278908 |
| **SEEDS India** | National | Disaster response, has a **partnership@** address — unusual and useful | partnership@seedsindia.org · 011-20904048 |

### Intermediaries — higher leverage than any single NGO

These can introduce you to many partners at once. Worth an email *early*,
because an introduction from them outranks a cold approach.

| Body | What it gives you | Contact |
|---|---|---|
| **Dasra** | Brokers between funders and 2,000+ NGOs; can name the right partner in each city | info@dasra.org · +91 22 6120 0400 |
| **Give.do** | 4,000+ vetted nonprofits; also a donation rail if you ever need public kit funding | support@give.do |
| **Sattva Consulting** | Impact advisory; sits between CSR desks and NGOs | impact@sattva.co.in |
| **India Development Review** | The sector's publication — a written piece here reaches every NGO leader in India | idronline.org (no public email found) |
| **Housing and Land Rights Network** | Documents homelessness *and* its criminalisation — see §11, they are the ones to pressure-test the privacy story | hlrn.org.in — **403 on fetch, get contact another way** |

**Ask an intermediary this, not a favour:** "Which two organisations in
[city] run night outreach for adult homeless people and would be willing
to test a dispatch tool?" A specific question gets a specific answer.

---

## 7. Quick commerce, delivery and corporate CSR — ask C

**The strategic point:** Section 135 of the Companies Act obliges large
Indian companies to spend 2% of net profit on CSR. That is money that
*must* be spent, and street welfare qualifies. You are not asking for
charity; you are offering a compliant place to put a budget line.

**Dunzo is dead** (insolvency, 2025). Do not include it in any deck.
**Zomato is now Eternal** — using the old name in an email dates you.

### The five best doors

**1 · Feeding India (Eternal/Zomato's CSR arm) — the single best fit.**
Already runs food distribution at street level, 82 cities, an existing
volunteer network. They have solved the logistics you are trying to
invent.
- `contact@feedingindia.org` · feedingindia.org
- Ask: co-branded kit supply for the pilot, or an introduction to their
  Delhi city lead.

**2 · Shadowfax — riders, and a real social-impact programme.** 100,000+
delivery partners, and a documented history of NGO logistics partnerships
during COVID.
- `hello@shadowfax.in` · shadowfax.in
- Ask: can a rider between orders take a kit run in one pincode.

**3 · Swiggy — the only one with a published sustainability address.**
Dark stores in dense neighbourhoods, ~690,000 riders, formal rider-welfare
programmes.
- `sustainability@swiggy.in` (also `secretarial@swiggy.in` for the CSR
  committee) · swiggy.com
- Ask: shelf space for 30 kits in one Instamart dark store in South-East Delhi.

**4 · Flipkart Foundation — the most formal partnership process.**
A dedicated CSR foundation with an explicit partnership framework, which
means a real process rather than a black hole.
- `flipkartfoundation@flipkart.com` · 080-67980000
- Ask: kit funding for a pilot.

**5 · IFAT (Indian Federation of App-based Transport Workers) — the
riders themselves.** 156,000+ gig workers organised. If you want riders as
responders, the union is a more honest door than the platform, and they
will tell you fast whether riders would want this or resent it.
- ifat.in (contact form; no public email found) ·
  Named: Prashant Bhagesh Sawardekar, National President

### The rest, and why they are harder

| Company | Depot potential | Door | Verdict |
|---|---|---|---|
| Blinkit | Excellent — dense dark stores | Only via Eternal/Feeding India | Go through Feeding India |
| Zepto | Good | `pr@zeptonow.com` (press) — no CSR channel found | Thin CSR story; low priority |
| BigBasket | Good | No published CSR channel; route via Tata | Slow |
| Amazon Now/Fresh | Good | No dedicated CSR email found. Named: Anita Kumar, Head of Amazon in the Community | Hard without a warm intro |
| JioMart | Good | Route via Reliance Foundation, not JioMart | Slow, but Reliance Foundation is huge |
| Delhivery | Logistics only | Only channel found is a whistleblower address — **do not use it** | Skip |
| Rapido / Ola / Uber / Porter / Zypp | Riders | No published CSR emails | LinkedIn or nothing |
| DMart Ready, Country Delight, Borzo | — | No CSR channel | Skip |

**Sequencing warning:** every one of these is worth more after a pilot.
A CSR desk funds evidence, not intentions. The exception is Feeding India,
who could plausibly help you *start*.

---

## 8. Nepal

**Recommendation: do not open Nepal before month 4, and do not open it at
all unless someone will be physically present.** A pilot you cannot attend
teaches you nothing when it fails. Nepal is a genuinely good second
market — harsh winters make the seasonal kit obviously valuable, and the
OpenStreetMap community there is world-class — but it is a second market.

### Practical context that changes the product

*Flagged by two independent researchers; verify before building.*
- **Messaging:** Viber and Facebook Messenger are far more dominant in
  Nepal than WhatsApp. Wayside's intake channel would need to change —
  and Viber is not currently supported. This is a real engineering cost,
  not a config change.
- **Emergency numbers:** reported as 100 (police), 102 (ambulance),
  104 (child search). Wayside's emergency gate is hard-coded to 112 and
  would have to be re-pointed. **Verify these numbers with a local source
  before writing a single line of code** — getting an emergency number
  wrong is the worst possible bug in this system.
- **Registration:** a two-tier process (District Administration Office +
  Social Welfare Council), reported at 4–6 weeks with annual compliance.
  A foreign-built tool almost certainly needs a local partner as the
  registered entity.
- **Smartphones:** ~70% penetration in Kathmandu Valley, with a
  significant feature-phone minority — an SMS fallback matters more here.

### NGOs — the five to approach

| Organisation | Why | Contact |
|---|---|---|
| **Manavsewa Ashram** | Directly specialises in street-homeless rescue, runs a 24/7 hotline, has an existing depot-like model. The closest match to Wayside in either country | manavsewa@msa.org.np · +977-9855076001 · Call centre 01-5979882 · Hetauda, Makwanpur |
| **Child Rescue Nepal** | 25 years, trained rescue staff, regional infrastructure | info@childrescuenepal.org · +977 1 5440737 · Patan Dhaka, Lalitpur |
| **Voice of Children** | Street outreach with drop-in centres, mental-health integration, Kathmandu Valley | info@voiceofchildren.org.np · +977-1-5429949 · Gwarko, Lalitpur |
| **Prisoners Assistance Mission** | Direct street-population outreach, nimble, Kathmandu-based | info@pam.org.np · +977 9851086523 · Raniban, Kathmandu |
| **Nepal Red Cross Society** | National infrastructure across 77 districts, winter relief capability | info@nrcs.org · +977-1-5370650 · Hotline 1130 · Kalimati, Kathmandu |

Also: **SASANE** (survivor-led, excellent safeguarding protocols — worth
consulting on dignity even if not a partner, +977-01-4547055);
**Umbrella Nepal** (info@umbrellanepal.org); **Himalayan Innovative
Society** (thisngonepal@gmail.com). **KOSHISH Nepal** (mental health and
homelessness) is highly relevant but no contact was findable — worth
chasing. **CWIN**'s site was unreachable during research.

### The technical ally worth more than any of them

**Kathmandu Living Labs** — the OpenStreetMap community in Nepal, who did
the post-earthquake mapping that became a global reference. Wayside runs
entirely on OSM. They are the one organisation in Nepal who would
immediately understand what you have built, and they have the map data
and the local credibility.
- `contact@kathmandulivinglabs.org` · +977-1-4720136 · kathmandulivinglabs.org
- **Approach them first, and as a peer, not a supplicant.** Ask about
  OSM coverage quality in Kathmandu and whether a street-aid dispatch
  layer interests them.

### Commercial and funding

| Organisation | Why | Contact |
|---|---|---|
| Nepal Telecom | Could zero-rate a reporting line so no witness pays to report | ntc.cco@ntc.net.np · +977-1-4210106 |
| Pathao Nepal | Largest rider network; depots and riders | 09610003030 (corporate delivery). Email on site is a placeholder — **not found** |
| Khalti | Payments, merchant network | support@khalti.com · 01-5970017 |
| Chaudhary Foundation | The largest private philanthropy in Nepal | info@chaudharyfoundation.org · +977-1-5522330 |
| Idea Studio Nepal | Startup incubator with national TV reach | info@ideastudio.org.np · +977 9802374601 |
| Shanker Group | CSR capacity | info@shankergroup.com · +977 1 4523733 |

**Tootle** is reported as still operating but with no usable corporate
contact. **Muncha** is a money-transfer service, not a delivery company —
ignore it despite what search results suggest.

---

## 9. Funding — ask B

**The single most useful finding: you do not need a legal entity for most
of these.** Eight of the top ten do not require one. Incorporating a
Section 8 company (₹5,000–10,000, 2–4 weeks) is *not* on the critical
path right now — it becomes necessary only for UNICEF's fund, Google.org
and Microsoft.

**Treat every deadline below as unverified.** The researcher's dates were
inconsistent and today is 10 August 2026 — several "2026 cycles" it
described as closed may have reopened, and one it listed as open may have
passed. Re-check every date on the funder's own page before you plan
around it.

### Apply now — no entity needed

| Funder | Money | Why it fits | Where |
|---|---|---|---|
| **Kevin Xu Innovation Challenge** | ~£25,000 non-dilutive | You are an Equitech alum and it is explicitly AI-for-social-impact. This is your warmest door anywhere in this document | equitechfutures.com |
| **Emergent Ventures** (Mercatus) | $1k–$50k | Rolling, no bureaucracy, no entity, no age floor. Built for exactly this | mercatus.org/emergent-ventures |
| **1517 Fund** | $50k+ | Explicitly funds students without credentials; rolling | 1517fund.com/grants |
| **Villgro** | up to ₹25 lakh + incubation | India's best-known social-enterprise incubator | villgro.org/incubation |
| **UnLtd India** | Incubation, little/no cash | Good for network and validation; be clear it is not money | unltdindia.org |

### Prepare for — bigger money, needs a pilot or an entity

- **Echoing Green Fellowship** — $100,000 over 18 months, no entity
  required, but fiercely competitive and annual. The best large prize on
  this list for you. Check when the next cycle opens.
- **Ashoka Fellowship** — needs a 1–3 year track record. Revisit after
  the pilot, not before.
- **UNICEF Venture Fund** — $50k–$400k equity-free, **requires a
  registered entity in a programme country** (India and Nepal both
  qualify). This is the reason to incorporate, when the time comes.
- **Hult Prize** — student-team competition, campus qualifiers typically
  in the autumn. Worth entering purely for the deadline discipline.
- **Google.org / Microsoft AI for Good** — both require a registered
  nonprofit. Park until incorporated.
- **Dasra's Rebuild India Fund** — flows through partner NGOs, so this
  unlocks *after* you have an NGO partner. Another reason ask A comes first.

### Not worth your time yet
Skoll (needs 5+ years of demonstrated impact), Gates/Wellcome Grand
Challenges (institutional applicants), Diana Award and Global
Undergraduate Awards (recognition, no money), Social Alpha (agri/climate
sector fit is weak), Thiel Fellowship (age-capped — check yours).

**One correction:** the researcher suggested `info@hultprize.org` while
admitting it had not found it. It is struck from this document. Do not
send mail to an address nobody has verified.

---

## 10. Government, public systems and the legal question

**Verdict: do not approach government before the pilot.** It is slow, it
is political capital you have not yet earned, and a rejection now closes
a door you will want open in month 6. One exception, below, is urgent.

### The urgent exception — the legal question

Wayside collects location data about a **third party who did not
consent**: the person on the street. This is the single highest-risk
thing about the entire project, and it is a legal question, not a design
one.

India's **Digital Personal Data Protection Act 2023** governs this. The
research found that non-profit exemptions exist but are not automatic,
that Wayside's design (no names, no photos required, 72-hour expiry,
coarse aggregates) already satisfies data-minimisation principles, and
that there is **no case law yet** because the Data Protection Board is
not operational. That last point cuts both ways: nobody can tell you
you are safe, and nobody can tell you you are not.

**Get a written legal opinion from an Indian data-protection lawyer
before the first real report is taken.** Estimated at ₹30,000–75,000 and
1–2 weeks. Budget it as a line item. This is the price of admission and
it is cheap next to the alternative.

**Questions to put to that lawyer:**
1. Does Wayside's data model trigger DPDP obligations at all, given no
   named individual is stored and records expire in 72 hours?
2. If it does, which lawful basis covers processing personal data about
   a person who has not consented and cannot easily be asked?
3. What is our liability if a partner NGO shares Wayside data with the
   police, and can we contractually prohibit it?
4. Does operating an emergency-adjacent service create any mandatory
   disclosure obligation to law enforcement?
5. What privacy notice must be displayed, and where — on the witness
   surface, at partner shelters, or both?
6. Does the answer change if a witness uploads a photo containing a
   recognisable face?

### The bodies, and when they matter

| Body | What it is | When to approach |
|---|---|---|
| **DUSIB** (Delhi Urban Shelter Improvement Board) | Runs Delhi's shelter network (~197 shelters reported). SPYM is already a contract partner | **After** the pilot, and *through* your NGO partner, not directly. Reported contacts: toll-free 14461, WhatsApp 9871013284 |
| **SMILE scheme** (Ministry of Social Justice & Empowerment) | Rehabilitation for people engaged in begging; reported expanding to 295 cities | Month 4+. Position Wayside as a *referral feeder*, never a competitor |
| **DAY-NULM / successor** (MoHUA) | The national urban-homeless shelter scheme. **Reported to have ended Sept 2024 with an unclear successor** | Verify what replaced it before citing it in any deck — a stale scheme name in a pitch is a credibility hit |
| **Delhi 112 / ERSS** | Unified emergency dispatch | **Ask one question now, in parallel: can an external service feed alerts into 112, or is it closed?** No public documentation exists either way. Wayside's design currently *redirects* to 112 rather than integrating, which is the safe default — confirm it must stay that way |
| **Nepal: Kathmandu Metropolitan City / Social Welfare Council** | Registration and municipal social welfare | Month 6+, and only with a local partner |

**The one thing to do now:** the legal opinion. Everything else on this
page waits for evidence.

---

## 11. Prior art, critics and advisors — ask D

### A correction before anything else

The research on this section asserted that Wayside has a "consent-first
design" in which the witness asks the person's permission before
reporting. **That is false. Wayside has no such feature.** The consent
mechanism in the codebase is a *rider* consenting to accept a job — the
researcher conflated the two. Do not repeat this claim to anyone. If you
want it to be true, it is a feature to build, and it may be the single
most valuable one on the roadmap.

### The closest analogue, and its documented failure

**StreetLink (UK)** — the public reports a rough sleeper; an outreach team
follows up. Operated in partnership between Homeless Link and Crisis
(sources disagreed on which; verify before citing). Reported at 60,000+
reports a year.

The research surfaced a critique attributed to the Museum of Homelessness
claiming a **~9% contact rate** — that of all those reports, fewer than
one in ten result in actual contact with the person — plus criticism that
it reports people without consent and functions partly as a government
data-collection pipeline.

**Verify that 9% figure at the source before you ever say it out loud.**
If it holds, it is the most powerful single number in your pitch: the
world's closest analogue to Wayside has a 91% miss rate, and you should
say what you are doing differently. If it does not hold, quoting it will
destroy your credibility with exactly the people who know this sector.

- thestreetlink.org.uk · homelesslink.org.uk · crisis.org.uk
- Critique: museumofhomelessness.org (search "the problem with StreetLink")

### The rest of the prior art

| System | Status | The lesson |
|---|---|---|
| **GoodSAM** | Alive | The first-to-accept-wins parallel dispatch you already copied. Proof the model works at scale, with ambulance-service integration. goodsamapp.org |
| **PulsePoint** (US) | Alive | Citizen dispatch with published outcome data, plus a public registry of where kits/AEDs are — directly analogous to your depot map. pulsepoint.org |
| **Ask Izzy** (Australia) | Alive | Two lessons: a **lived-experience advisory group** shaping the design, and **zero-rated carrier access** so a person with no credit can still use it. Both are things Wayside lacks. askizzy.org.au |
| **Miracle Messages** (US) | Alive | Frames homelessness as *relational* poverty, not only material. Reportedly expanding into South Asia — check whether they are a collaborator or a competitor. miraclemessages.org |
| **Robin Hood Army** (India) | Alive | **Deliberately refuses to build an app** for the last mile, and coordinates 50,000+ volunteers over WhatsApp. Ask them why. Their answer is the strongest challenge to Wayside's existence, and you should hear it before an investor asks it |
| **Rain Basera / DUSIB apps** (Delhi) | Alive, limited | Government shelter-bed apps. Shows the state's version exists and is thin — and that nobody in India is doing witness-dispatch |

### The critique you must be able to make better than your critic

The strongest version: *location-based reporting of vulnerable people
creates infrastructure that outlives its intentions.* Data gathered to
help gets used to plan hostile architecture, to justify "move-along"
enforcement, and to target policing. People who know they may be reported
hide — from help as much as from harm. Virginia Eubanks' **Automating
Inequality** is the canonical statement of this; **Housing and Land Rights
Network** documents the Indian version, where homelessness is
criminalised in practice.

Wayside's architectural answer: no person-index, no photo requirement,
72-hour case expiry, pins deleted, only coarse 90-day cell counts, and
dispatch to NGO workers rather than police.

**Where that answer is weak, and you should say so first:**
- If a partner NGO shares data with police, the architecture does not
  save you. The mitigation is contractual, not technical — and you have
  not written that contract yet.
- The person reported still had no say. Aggregate privacy is not consent.
- "Trained responder" is only as good as the partner's vetting.

### Five people to ask for advice, not money

1. **Housing and Land Rights Network** — *"How could this be co-opted for
   surveillance or eviction, and what safeguards would you demand?"* They
   will give you the hostile case in full, which is exactly what you need.
2. **Aashray Adhikar Abhiyan** (Sanjay Kumar, formerly homeless twelve
   years) — *"Would you have wanted a stranger to report you?"* No one
   else on this list can answer that.
3. **Robin Hood Army** — *"You chose not to build an app. Why?"*
4. **Homeless Link / StreetLink operators** — *"If you were rebuilding
   StreetLink for India, what would you fix first?"*
5. **Gautam Bhan** — India's leading researcher on urban homelessness and
   housing (at **IIHS**, Bengaluru — the research misattributed him to
   "IIEG"; verify the affiliation before writing). Ask what structural
   risk a dispatch tool is blind to.

**Dropped from the researcher's list:** an advisor entry describing "Kevin
Xu of MIT/Context Labs" appears to be a confusion with the Kevin Xu
Innovation Challenge, and is unreliable. Also worth contacting instead:
the **Humanitarian OpenStreetMap Team (HOT)**, since Wayside is built
entirely on OSM.
