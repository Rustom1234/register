# Plan deep-dive — how each version actually works

Each version is explained as: goal → moving parts → what you personally build → money → metrics → risks. Then a worked example. All three examples deliberately reuse the same situation — the man with the wrapped, bleeding foot — so the differences between versions are visible in what happens to *him*.

---

## Version A — "Supply Line"

**Goal:** put a standardized aid kit into the hands of the people who already find those in need (outreach teams, mobile medical vans, winter rescue vans), and quietly test the paid-rider logistics rail behind them. No public-facing anything.

### The moving parts

**The kit (~₹300 all-in, everything OTC).** Designed in one workshop with Goonj's ops team and your outreach partner's clinical lead — the clinical lead owns the contents list, you own the logistics:

- *Wound care:* antiseptic liquid, sterile gauze, crepe bandage, adhesive dressings, micropore tape, disposable gloves — the exact things that would have changed that man's week.
- *Health basics:* ORS sachets, glucose. (Tablets only if the clinical partner approves — stay conservative on Drugs & Cosmetics Act lines.)
- *Hygiene:* soap, small towel; cloth sanitary pads from Goonj's "Not Just a Piece of Cloth" line where relevant.
- *Season:* monsoon = raincoat/umbrella/tarp; winter = blanket or sleeping bag from Goonj's Odha Do Zindagi stock.
- *Info card in Hindi:* nearest shelters (DUSIB list), helpline 14461, the mobile medical van's schedule. The kit should leave a thread back to services, not just supplies.
- *Packaging:* a cloth bag sewn from Goonj surplus fabric — dignified, reusable, on-ethos.

Cost math: ~₹150–200 purchased items + Goonj surplus (processing contribution ~₹50–100) + bag ≈ ₹300.

**The flow.**
1. Goonj's processing center assembles 200–500 kits — the same muscle they use for Rahat disaster family kits, so this is a small ask for them.
2. The outreach partner's teams carry 20–30 kits per shift on their normal rounds. Every handover is logged in ~20 seconds on a phone form: area (not exact pin — dignity), need category, accepted/refused, escalated yes/no.
3. **The restock loop is where the delivery rail gets tested.** When a team drops below ~5 kits, they send a code word on WhatsApp; you dispatch a paid two-wheeler rider (Porter or similar, ~₹80–150/run, normal commercial rates) with a case of 25 from Goonj's center to wherever the team is. You log the turnaround time. This is the entire "gig fleet moves aid" concept in miniature — with zero rider-to-vulnerable-person contact.
4. Weekly review: kits out, needs by category and area, escalation count, restock latency, all on a Sheet + map.

**What you personally build:** the kit spec document, a Google Form → Sheet → Looker Studio map, the WhatsApp restock protocol, and a one-page SOP. Two weekends of work. The scarce input isn't code — it's the two partnership conversations.

**Money:** ~₹3–5L for 90 days (300–500 kits, delivery fees, printing, contingency). Fundable out of pocket / friends-and-family / a single small grant.

**Metrics:** kits distributed per week; acceptance rate; % escalated to clinical care; restock turnaround; all-in cost per kit delivered; field notes on what people actually ask for (this reshapes kit v2).

**Risks:** it's invisible — a supply-chain upgrade, not a product, so momentum depends entirely on partner energy (mitigate: one team, one geography, weekly rhythm); kit contents disputes (clinical lead decides, full stop); winter/monsoon seasonality (time the launch to a season, don't fight it).

### Worked example

It's a Tuesday in monsoon season. The partner's mobile health van is doing its regular Nizamuddin round — a route it has run for two years, staffed by a paramedic and an outreach worker named (say) Meena. Meena knows most of the regulars; she spots a man she hasn't seen before, sitting under the flyover with a wrapped foot, blood showing through.

Because of Version A, the van isn't just carrying its medical bag — it has 24 of your kits on the shelf. The paramedic unwraps the foot, cleans it with the kit's antiseptic, re-dresses it properly, and doesn't like what he sees — early infection — so he books the man for Thursday's dressing change and notes him for the doctor's next van day. Meena hands over the kit bag: remaining dressings, ORS, soap, socks, a raincoat, and the info card with the van's schedule. She taps four fields on her phone: *wound care · accepted · escalated: yes · Nizamuddin zone.* Total added time: three minutes.

By Thursday the van is down to 4 kits. Meena WhatsApps "RESTOCK N-2". You book a Porter rider; 40 minutes and ₹120 later a case of 25 kits from Goonj's center is in the van. At month end your dashboard says: 240 kits distributed, 71% of cases in that zone were wound/skin-related, 12% escalated, restock median 55 minutes, ₹332 per kit delivered all-in. That last slide is what you'll show Goonj's leadership — and it's slide 1 of the Version B pitch.

**What did *not* happen:** nobody photographed him, no database knows he exists, no untrained stranger approached him — and he got clinical eyes on the foot, which a kit alone would have missed.

---

## Version B — "Signal Loop"

**Goal:** open the front door. Anyone who sees someone in need can report in 90 seconds; a verified human closes every loop; Version A's supply line does the fulfilment. This is the product nobody in the world has built.

### The moving parts

**1. The reporting bot** (WhatsApp Business API via Gupshup/Wati — no app to install, which in India is the whole game):
- Flow: share location pin → "what do you see?" (1 injury/wound · 2 needs rain/cold protection · 3 hungry · 4 needs shelter · 5 emergency) → optional photo → "how long ago?" → report ID.
- Option 5 immediately redirects: "Please call 112 now" — the bot is never an emergency service, and says so.
- The reporter later gets a closure message: "An outreach worker reached the person you reported. Thank you for stopping." That message is your growth engine — it converts one-time reporters into repeat ones.

**2. The verification dashboard** (Appsmith/Retool, or honestly a Sheet for the first month):
- Queue with map, report age, category, photo; duplicates within ~100m/2h auto-merge.
- Statuses: new → assigned → found / not found → served → escalated → closed. Unverified reports **auto-expire at 72h.**
- Category "injury/wound" fires an instant alert to the clinical team's lead — the escalation path is wired in from day one, because the worst failure mode is a kit substituting for care.

**3. Dispatch:** verified reports get folded into the outreach team's next round; speed-critical cases (injury, monsoon night) trigger a paid rider run — but the rider delivers **to the outreach worker heading there**, never directly to the person. Version A's restock rail, pointed at a spot.

**4. Privacy by architecture** (this is what makes the whole thing DPDP-proof and dignity-proof): no names or IDs of subjects; photos deleted on case close or at 72h; analytics keep only coarse area cells; reporter numbers hashed. You publish a monthly *aggregate* heatmap — advocacy gold — never a live or granular one. The dangerous database never exists, so it can never be demanded, leaked, or subpoenaed into a sweep.

**5. Seeding volume** (the cold-start plan): QR posters at chemists, tea stalls, and petrol pumps in ONE zone; RWA WhatsApp groups; auto and delivery drivers (informally at first); security guard agencies; college NSS units. Density in one zone beats thin coverage of a city. The later unlock: pitch one platform to add a one-tap "person needs help here" flag in the rider app — 100k human sensors who pass every street daily, zero cameras.

**6. ML, eventually and only on reports:** triage/prioritization and duplicate detection over report text and photos (the DSSG × Homeless Link precedent), hotspot prediction to route vans. This is the legitimate AI roadmap — learning from *witness reports*, not surveilling strangers.

**Money:** ~₹8–15L over 6 months including the embedded Version A: bot fees (~₹5–10k/mo), a paid coordinator (~₹25–30k/mo — the single most important hire; verification SLA is the product), kits, rider fees, printing.

**Metrics — the StreetLink-lesson set:** reports/week; % actionable; median report→verification time; **found rate** (StreetLink managed only 23% — beat it with photo + freshness prompts and a tight zone); served rate; acceptance rate; escalation rate; repeat-location rate; **cost per verified need served.**

**Kill criteria, written before launch:** verified-need rate <40%; acceptance <50%; cost per verified need >3× kit cost; partner backlog growing week over week. If any trips for a month, stop and rethink rather than drift.

### Worked example

Same man, same flyover — but this time *you* are the sensor, three weeks into the pilot. You walk past him on your way to lunch. Instead of the helpless feeling that started this whole project, you stop for 90 seconds: scan the QR you've saved from a chemist's poster, share the pin, tap **1 — injury/wound**, take one photo from a respectful distance, send. The bot replies with report #0847 and one line: "If this is a medical emergency, call 112."

At the dashboard, the coordinator sees #0847 come in at 1:12pm, notices it's 400m from where the health van is parked on its Tuesday round, and assigns it to Meena with the photo. The wound category has already pinged the paramedic's phone. By 2:05pm Meena finds him — his name, it turns out, is Ramesh — and the Version A playbook runs: wound cleaned and re-dressed, infection flagged, Thursday follow-up booked, kit and raincoat handed over. She closes the case on her phone: *found ✓ · served ✓ · escalated ✓.* The photo is deleted automatically. At 2:31pm your phone buzzes: "An outreach worker reached the person you reported today. Thank you for stopping." You will absolutely report the next person you see — that message is why.

On Thursday the van returns for the dressing change — the loop, not the kit, is what actually heals the foot. And on the monthly aggregate map, Ramesh's cell ticks to 4 wound cases this month, so the van's Tuesday route shifts 500m south. That's what "ML on reports, not cameras" looks like in embryo.

**Compare with Version A:** Ramesh no longer has to be lucky enough to sit on an existing van route. Any of the ~5,000 people who walked past him that day could have been his sensor.

---

## Version C — "Aid Drops"

**Goal:** make the loop platform-native. Zomato/Blinkit already own every ingredient — the ₹1–10 checkout-donation rail (which funds Feeding India's 200K meals/day), dark stores, a rider network, an NGO web, and demonstrated appetite for humanitarian logistics (25 ambulances in NCR). Nobody has connected them to street level. You bring the one thing they can't credibly build in-house: the **verification and outcomes layer.**

### The moving parts

- **Funding:** an "Add ₹5 for a street aid kit" toggle at checkout (the gesture Feeding India already normalized), 80G receipts via the foundation, CSR budget tops up the gap.
- **Supply:** Goonj kits staged in 2–3 dark stores per pilot zone, replenished weekly.
- **Demand:** verified need-spots flow from your Signal Loop — now including the official **one-tap rider flag** in the platform's own app, which turns every rider into an opt-in sensor.
- **Fulfilment — the "Aid Drop" order type:** opt-in riders only; a 30-minute training module (dignity, consent, safety, you-are-not-a-medic); deliveries go to an outreach worker or a marshalled distribution point, never directly to an unaccompanied stranger; standard pay, no rating penalty, daylight hours only. Under Karnataka-style gig law this is a formal contract/algorithm change with 14-day notice — the platform's legal team drives that, your MoU anticipates it.
- **Governance (the part that keeps everyone safe):** the platform never receives subject-level data — only anonymized spots and outcome counts; location data is never shared with authorities (non-negotiable, given Indore/SMILE-style enforcement drives); liability split and brand rules in the MoU; your org publishes the metrics that make their ESG story auditable.
- **The path in:** month 6+, with Signal Loop numbers in hand — "X verified needs served at ₹Y each, Z% acceptance, escalation working" — via Feeding India's partner-NGO door or Blinkit's CSR/ambulance team (their CEO called ambulances "uncomfortable territory" and did it anyway — that's your buyer). Propose a 90-day co-pilot: one zone, 1,000 kits, 3 dark stores, 50 opt-in riders.

**Money:** the program runs on platform money (checkout donations + CSR); your costs are the verification layer and BD time. Your organization's sustainability question becomes "who funds the orchestrator" — typically a per-kit orchestration fee inside the CSR grant.

**Metrics the platform will care about:** kits deployed, people served, cost per person served, clinical escalations completed, rider opt-in and satisfaction rates, zero-incident record — plus everything from B.

**Risks:** the platform will want to own the story (accept it — take the scale, keep the data governance); champion churn orphans programs (multi-year MoU, published metrics); a single rider incident can kill it (hence the deliver-to-worker rule and daylight-only policy); political entanglement with "begging-free city" drives (stay visibly on the aid side; never co-locate with enforcement).

### Worked example

Eighteen months from now, Gurugram pilot zone. A customer in Sector 56 orders dinner on Zomato and taps the ₹5 aid-kit toggle — one of ~40,000 such taps in the zone that month, ≈₹2L, enough to fund ~600 kits.

That same morning, a Blinkit rider on a grocery run passes a flyover and sees a man with a bandaged, bleeding foot. He doesn't stop — he's mid-delivery — but he long-presses the **flag** button in his rider app: pin dropped, category "injury", eight seconds, back on the road. The flag lands in your verification queue alongside two citizen WhatsApp reports from the same cell (auto-merged: one case, not three).

Your coordinator verifies with the zone's outreach partner and batches it into Thursday's run. At 11am Thursday, rider Suresh — opted into Aid Drops last month, took the training — gets a task between lunch orders: collect 6 kits from the Sector 57 dark store, deliver to outreach worker Meena at a pinned corner 2.8km away. Standard payout. He hands the case to Meena and is back on food orders in 20 minutes; he never approaches anyone vulnerable, and his rating can't be touched by the detour.

Meena's team works the three verified spots that afternoon. Under the flyover, the paramedic treats the flagged man's foot — cleaned, dressed, booked for follow-up — and he keeps a kit. Case closed in the system: *6 kits deployed · 5 people served · 1 clinical escalation · ₹41 per person served.* The platform never learns his name; it receives a monthly outcomes page for its ESG report — which is precisely why the program survives the next budget review, where CSR pilots usually go to die.

**Compare with Version B:** the sensor network went from your posters to a fleet of thousands; the funding went from grants to a self-replenishing checkout rail; and your role sharpened into the thing with defensible value — the trusted verification and outcomes layer between platforms, NGOs, and the street.

---

## Side-by-side

| | A — Supply Line | B — Signal Loop | C — Aid Drops |
|---|---|---|---|
| One-liner | Kits + logistics for existing outreach | Public report → verify → dispatch → outcome loop | The loop as a platform-native program |
| Sensor | Outreach teams' own eyes | Citizens + (later) riders, via WhatsApp | Official rider-app flag + citizens |
| Who touches the person | Trained outreach/clinical staff | Same | Same (riders deliver to workers only) |
| You build | Kit spec, log sheet, restock SOP | Bot, dashboard, metrics spine | Verification layer + MoU + governance |
| Cost to you | ₹3–5L / 90 days | ₹8–15L / 6 months | Mostly BD time; platform funds ops |
| Time to first person helped | ~3 weeks | ~6 weeks | 6–12 months |
| Novelty | Low (but real gap) | High — the loop exists nowhere | Highest — global first for a platform |
| Main risk | Invisible; partner energy | Report noise; verification capacity | Sales cycle; platform politics |
| What it proves | Demand density, kit economics | The loop works; found/served rates | Scale + sustainable funding |

**Sequence, not choice:** A is B's fulfilment backbone; B's data is C's admission ticket. Start A with one Goonj conversation; B goes live within the quarter; C is a month-6 pitch made with numbers instead of a story.
