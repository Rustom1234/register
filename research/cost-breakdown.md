# Wayside — the money page

*What it costs to run Wayside, in plain language. One page, no jargon.
Every number is either **sourced** (with the document and section it comes
from) or clearly marked as an **estimate** with the reasoning behind it.
Companion docs: [build-plan.md](./build-plan.md) ·
[product-plan.md](./product-plan.md) ·
[pitch](./pitch/wayside-kxic-pitch.md).*

*Currency: Indian rupees (₹). Where a source is in US dollars we show
both, converted at roughly ₹85 per dollar (estimate — rate of mid-2026).*

---

## 1. One-time costs (before the pilot starts)

| Item | Cost | Basis |
|---|---|---|
| Aid kits — initial stock (~100 kits: medical, food, weather) | **~₹30,000** | Estimate. ~₹300 per kit (pitch §9, unit economics); 100 kits covers the first weeks of an 8-week pilot with restocking to follow (see §4) |
| Rider phones | **₹0 expected** | Riders use their own Android phones; the rider app installs from a link, no store, no special hardware (product-plan, Phase 2). *If* a partner NGO asks us to provide phones: estimate ~₹8,000–10,000 per basic Android handset — a founder/partner decision, not assumed here |
| Domain name (website + chat line address) | **~₹800–2,000 / year** | Sourced: product-plan, "Decisions only the founder can make" |
| Zone seeding — QR posters, printed cards for guards/shops/RWA groups | **~₹2,000–3,000** | Estimate. Ordinary print-shop rates for one pilot zone; seeding method sourced from build-plan §8 (P2) |
| Misc. one-time (SIM for the public number, small supplies) | **~₹1,000–2,000** | Estimate |

**One-time total: roughly ₹35,000–37,000** (estimate; dominated by the
kit stock, which is the point — see §5).

## 2. Monthly running costs

| Item | ₹ / month | Basis |
|---|---|---|
| Hosting (one small server + database, Fly.io, Mumbai region) | **~₹450–1,300** ($5–15) for the lean pilot setup; up to **~₹1,700–2,600** with the full ops dashboard stack | Sourced: build-plan §2 (hosting decision) and §7 (costs table). The lower band is the minimum that runs the pilot; the higher band adds the coordinator dashboard container |
| WhatsApp messages (when the official Meta line is switched on) | **~₹150–300** | Sourced: build-plan §7. Incoming messages and replies within Meta's 24-hour window are **free**; only the occasional "case closed" notification (~₹0.115 each) costs money. Meta's free monthly tier covers a pilot's volume (product-plan, Phase 4) |
| Telegram chat line (the immediate, no-approval alternative) | **₹0** | Sourced: product-plan, Phase 4 — Telegram bots are free to run |
| Map and routing data | **₹0** | Sourced: product-plan, Phase 1 — open street data (OpenStreetMap), self-hosted, restyled; no Google key, no per-view fees, ever |
| AI report-reading (turning a witness's message/voice note into a structured case) | **~₹1,300** at ~50 reports/week; **~₹5,200** at the 200/week ceiling | Sourced: build-plan §7 — ~₹6 per report, all AI and speech-to-text included. **Deployment-time choice:** this line exists only when a funded deployment enables the live AI backend; every demo and test today runs on a free built-in mock, at ₹0 |
| Address lookup (geocoding) | **₹0** | Sourced: build-plan §2 — the free tier (10,000 lookups/month) covers pilot volume |

**Monthly tech total: roughly ₹3,000–4,000 at realistic pilot volume
(~50 reports/week), ceiling ~₹7,000–8,000 at 200 reports/week** —
sourced: build-plan §7. Kits and responder stipends, not technology,
are the real recurring cost (next section).

## 3. Cost per person served — against the kill line

| | ₹ | Basis |
|---|---|---|
| Kit (medical / food / weather) | **~₹300** | Sourced: pitch §9 |
| Delivery + share of running costs | **~₹130** | Derived: pitch §9 gives ~₹430 all-in per person served |
| **All-in cost per person served** | **~₹430** | Sourced: pitch §9 (unit economics to be defended in the pilot) |
| Current figure on the live kill-criteria dashboard | **₹580** | Sourced: pitch §12 (demo data) |
| **Kill line — pre-registered, public** | **≤ ₹900** | Sourced: pitch §9 and §12 |

If the pilot cannot serve a person for under ₹900 all-in, Wayside's own
dashboard says so, we publish that, and we stop. That promise is made
before the pilot starts (pitch §12).

## 4. The 8-week, one-zone pilot — total

Assumptions (all estimates, stated so they can be challenged): one zone
(Nizamuddin, per pitch §9); ~50 reports/week (build-plan §7's realistic
band, not its 200/week ceiling); the pre-registered target of at least
40% of reports leading to a verified, served need (pitch §12) — call it
~150–200 kits over 8 weeks. Responder stipends are set with the partner
NGO, not by us; the placeholder below is an estimate to be replaced by
the partner's real figure.

| Line | ₹ | Basis |
|---|---|---|
| Kits (~200 served × ₹300, incl. restocks beyond the initial 100) | **60,000** | Estimate built on the sourced ₹300/kit (pitch §9) |
| Delivery + running share (~200 × ₹130) | **26,000** | Derived from the sourced ₹430 all-in figure (pitch §9) |
| Technology, 2 months (hosting + WhatsApp + AI at ~50 reports/week) | **8,000** | Sourced: build-plan §7 (₹3–4k/month band, rounded up) |
| Domain, one year | **2,000** | Sourced: product-plan (top of the ₹800–2,000 range) |
| Zone seeding + misc one-time | **5,000** | Estimate (§1 above) |
| Responder stipends, 8 weeks | **to be set with the NGO partner** — placeholder ~₹40,000 (est. 6–10 part-time riders, pitch §11) | Estimate only; the partner's own pay scales govern |
| Contingency (~10%) | **14,000** | Estimate; standard buffer |
| **8-week pilot total** | **≈ ₹1,55,000 (~₹1.1 lakh excluding stipends)** | Sum of the above; every line marked sourced or estimate |

Read it the way we do: **over 90% of the money goes to kits, delivery,
and the people doing the serving.** The technology is under ₹10,000 of
the whole pilot — deliberately (build-plan §9: the system is designed to
run on a single modest recurring donor).

## 5. What is deliberately ₹0 — and why

| ₹0 line | Why it's free by design |
|---|---|
| Map display and road routing | Self-hosted open street data (OpenStreetMap) styled to read like a familiar consumer map — no Google Maps key, no per-load fees (product-plan, Phase 1) |
| Map tile server | Tiles are generated and served from our own small server; no third-party tile subscription (product-plan, Phase 1) |
| Demos, testing, and this working system today | Everything you can be shown right now — control room, rider app, witness chat, 111 automated tests — runs on a built-in mock AI backend with **zero paid API calls** (pitch §7). Paid AI is switched on only by a funded deployment, with its cost shown in §2 |
| Telegram chat line | Free to operate, no approval queue — lets field testing start while WhatsApp verification is pending (product-plan, Phase 4) |
| Incoming WhatsApp messages | Free under Meta's pricing — a witness reporting never costs the project anything (build-plan §2, §7) |
| Coordinator dashboard software | Open-source, self-hosted, unlimited users (build-plan §2) |

The pattern is the principle: **money goes to the person on the
pavement, not to software licences.** Where a free, self-hosted, or
open-source path existed, it was built in from the start — which is also
why the monthly bill stays small enough for one modest donor to carry
(build-plan §9).

---

*Prepared from the project's research corpus, August 2026. Figures
marked "estimate" are honest planning numbers, not quotes; the pilot's
job is to replace them with measured ones, published on the same
dashboard the funders see.*

*Kit contents are itemized separately with source-linked Delhi prices in
[`kit-costs.md`](kit-costs.md): per-kit ≈ ₹172 MED / ₹50 FOOD / ₹173 SEAS
at wholesale, one-time depot seeding ≈ ₹6,900, and a year-1 stock budget
of ≈ ₹36,500 including 15% contingency.*
