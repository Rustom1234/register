# Wayside — live vendor pricing research (August 2026)

*Independent price check for the pilot's cost model: Delhi, one zone,
~50 reports/week realistic, 200/week ceiling (~870/month). Every number
below is either **sourced** (link + accessed date) or explicitly marked
**estimate**. Conversion used throughout: **~₹87 per US dollar (estimate,
early-Aug 2026 spot; the companion cost doc uses ₹85 — both are stated
so either can be swapped in).* Researched 2026-08-04 via web search;
several vendor pages (fly.io, docs.sarvam.ai, aisensy.com) blocked
direct fetching from this environment, so those rows rest on search
snippets of the vendor page plus third-party trackers — flagged inline.*

---

## 1. WhatsApp Business Cloud API (Meta direct) — India, 2026

Meta switched from per-24-hour-conversation billing to **per delivered
template message** on **1 July 2025**. Service conversations (user
messages in, and any free-form replies within the 24-hour customer
service window) became **free and unlimited on 1 Nov 2024**, replacing
the old 1,000-free-conversations monthly tier. Meta then raised India
marketing rates ~10% on **1 Jan 2026**.

| Item | Rate (India) | Source (accessed 2026-08-04) |
|---|---|---|
| Incoming messages (witness reports) | **₹0 — free, unlimited** | [Blueticks 2026 pricing guide](https://blueticks.co/blog/whatsapp-business-api-pricing-2026); [EngageLab guide](https://www.engagelab.com/blog/whatsapp-business-api-pricing) |
| Replies within 24-h service window | **₹0** | Same sources (service conversations free since 2024-11-01) |
| Utility template message (e.g. "case closed" outside window) | **~₹0.115 per message** (some trackers show ₹0.12–0.13) | [Whautomate India rate card](https://whautomate.com/whatsapp-business-api-pricing-india); [RichAutomate](https://richautomate.in/blog/whatsapp-business-api-cost-india-2026) |
| Authentication template | ~₹0.115 (not used by Wayside) | Same |
| Marketing template | **₹0.8631** (up from ₹0.7846 on 2026-01-01) — not used by Wayside | [Whautomate](https://whautomate.com/whatsapp-business-api-pricing-india); [Blueticks](https://blueticks.co/blog/whatsapp-business-api-pricing-2026) |
| Meta platform/monthly fee for Cloud API direct | **₹0** — Meta charges per message only | [2Factor guide](https://2factor.in/v3/lp/whatsapp-business-api-pricing.php) |

**Pilot arithmetic (estimate):** even if every one of ~870 monthly
reports at the ceiling got one paid utility notification, that is
870 × ₹0.115 ≈ **₹100/month**. Realistically most closures land inside
the free 24-h window, so **₹0–150/month**.

### Going through a BSP instead of Meta direct

| Provider | Platform fee | Per-message on top of Meta | Source (accessed 2026-08-04) |
|---|---|---|---|
| **Meta direct (Cloud API)** | ₹0 | ₹0 | above |
| **Twilio** | ₹0 monthly | **+$0.005/message (~₹0.44) both directions** — i.e. even free incoming messages cost money | [Zernio Twilio breakdown](https://zernio.com/blog/twilio-whatsapp-pricing-breakdown-what-it-really-costs); [Authgear guide](https://www.authgear.com/post/whatsapp-api-pricing/) |
| **Gupshup** | Starter ~$39.99/mo (~₹3,500) + per-conversation platform fee | varies | [Authgear guide](https://www.authgear.com/post/whatsapp-api-pricing/) |
| **AiSensy** | Basic **₹1,500/mo** (Pro ₹3,200/mo); free tier exists with limits | Marked-up Meta rates: utility **₹0.145** (vs Meta ₹0.115, ~26% markup), marketing ₹1.09; service convos free | [AiSensy pricing page (via search)](https://aisensy.com/pricing); [Chatbotscape review](https://chatbotscape.com/reviews/aisensy-review) |
| **360dialog** (cleanest pass-through per trackers) | ~$49/mo (~₹4,300) | flat $0.005/msg | [Authgear guide](https://www.authgear.com/post/whatsapp-api-pricing/) |

**Conclusion (research judgment):** at Wayside's volume, every BSP adds
₹1,500–4,500/month of pure overhead for convenience features (campaign
dashboards) the pilot doesn't need. **Meta Cloud API direct is the
right call and costs ≈ ₹0–150/month.** Twilio is the worst fit — its
per-message fee applies to *incoming* messages, taxing exactly the
thing Meta gives free. (AiSensy exact plan tiers: could not open
aisensy.com directly from this environment; ₹1,500 Basic figure is the
snippet of AiSensy's own pricing page plus a third-party review —
treat ±₹500.)

---

## 2. Small-app hosting (512MB–1GB Python app + SQLite/small Postgres)

| Option | Monthly (USD) | Monthly (₹ @87) | Notes | Source (accessed 2026-08-04) |
|---|---|---|---|---|
| **Fly.io** shared-cpu-1x, 256MB | ~$1.94–2.02 | ~₹170–175 | Mumbai (`bom`) region available; compute priced per machine size | [Fly resource pricing (index)](https://fly.io/docs/about/pricing/) via [Kuberns](https://kuberns.com/blogs/flyio-pricing/), [ToolRadar](https://toolradar.com/tools/flyio/pricing) |
| **Fly.io** shared-cpu-1x, **512MB** | **~$3.19** | **~₹280** | sweet spot for the FastAPI app + embedded SQLite on a small volume | [Northflank comparison](https://northflank.com/blog/railway-vs-flyio); community/docs echoes |
| **Fly.io** shared-cpu-1x, **1GB** | **~$5.70** | **~₹500** | headroom for dashboard container or Postgres | Same |
| Fly.io volume storage | ~$0.15/GB/mo | ~₹13/GB | a 1–3GB SQLite volume is pennies | [Fly cost management](https://fly.io/docs/about/cost-management/) (page blocked to direct fetch; figure widely echoed) |
| Fly.io egress, **India** | **$0.12/GB** (vs $0.02 NA/EU) | ~₹10/GB | pilot traffic is tiny (text + occasional images); estimate <5GB/mo → <₹55 | [Deploy Handbook](https://deployhandbook.com/pricing/fly-io) |
| Fly.io free tier | **None any more** — pay-as-you-go from the first machine | — | old free allowances retired | [SaaSPricePulse free-tier explainer](https://www.saaspricepulse.com/blog/flyio-free-tier-2026) |
| **Railway** Hobby | $5/mo, includes $5 usage; small Python service typically **$10–15/mo** all-in | ~₹440 min, ~₹870–1,300 typical | RAM $10/GB/mo, vCPU $20/mo — costs creep with a DB | [Railway calculator](https://makerkit.dev/pricing-calculator/railway); [Northflank](https://northflank.com/blog/railway-vs-render) |
| **Render** Free | $0 | ₹0 | web service **spins down when idle** — bad for a live aid line | [Encore comparison](https://encore.dev/articles/render-vs-railway) |
| **Render** Starter | $7/service/mo; comparable stack lands $21–34/mo with DB | ~₹610/service | per-service pricing punishes multi-container setups | [DevToolPicks](https://devtoolpicks.com/blog/railway-vs-render-vs-fly-io-solo-developers-2026) |

**Conclusion:** Fly.io Mumbai remains the cheapest always-on option:
**~₹300–550/month** for one 512MB–1GB machine + volume + egress
(estimate built on sourced unit prices); **~₹800–1,100/month** if a
second machine runs the ops dashboard. Note: exact fly.io pricing page
was 403-blocked from this environment; the $1.94/$3.19/$5.70 figures
are consistent across three independent 2026 trackers.

---

## 3. Hindi/Hinglish speech-to-text (per minute)

| Provider / model | Price | ₹/min @87 | Hinglish fit | Source (accessed 2026-08-04) |
|---|---|---|---|---|
| **Sarvam AI — Saarika/Saaras STT** | **₹30/hour = ₹0.50/min** (docs also quote $0.35/hr; +diarization $0.53/hr). ₹1,000 free credits on signup. Saarika v2.5 deprecating in favour of **Saaras v3** | **₹0.50** | Built for Indian languages incl. code-mixed Hindi-English; the strongest claim to street-noise Hinglish | [Sarvam API pricing](https://www.sarvam.ai/api-pricing); [Sarvam docs pricing](https://docs.sarvam.ai/api-reference-docs/pricing) (docs page blocked to direct fetch; figures from vendor-page search snippets) |
| OpenAI `gpt-4o-mini-transcribe` | $0.003/min | ~₹0.26 | good multilingual, less Indic-tuned | [CloudZero OpenAI pricing](https://www.cloudzero.com/blog/openai-pricing/); [InvertedStone calculator](https://invertedstone.com/calculators/whisper-pricing) |
| OpenAI `gpt-4o-transcribe` / `whisper-1` | $0.006/min | ~₹0.52 | solid Hindi; Hinglish code-switching weaker than Indic-specialist models (estimate/judgment) | Same |
| Google STT v2 (standard) | $0.016/min (batch/dynamic $0.003/min) | ~₹1.39 (batch ~₹0.26) | supports hi-IN; priciest for real-time | [Google STT pricing](https://cloud.google.com/speech-to-text/pricing); [DIYAI breakdown](https://diyai.io/ai-tools/speech-to-text/google-cloud-speech-to-text-pricing/) |

**Pick: Sarvam Saaras at ₹0.50/min** — within ~2× of the absolute
cheapest, Indic/Hinglish-specialised, Indian company, INR billing, and
₹1,000 free credits covers the whole pilot's likely usage (≈33 hours of
audio). Cheapest-on-paper is OpenAI mini at ~₹0.26/min if quality on
noisy Hinglish tests out. **Estimate:** if ~40% of ~870 ceiling-volume
reports are one-minute voice notes → ~350 min/month → **₹90–175/month**
(and ₹0 until free credits run out).

---

## 4. AI text extraction per report — Claude Haiku 4.5 (deployment-time choice)

Per this repo's rules, this line is **switched on only by a funded
deployment**; all demos/tests run on the free mock backend at ₹0.

| Item | Value | Source (accessed 2026-08-04) |
|---|---|---|
| Haiku 4.5 input | **$1.00 / M tokens** | Anthropic model pricing (per bundled claude-api reference, cached 2026-06-24; live page [platform.claude.com/docs/en/pricing](https://platform.claude.com/docs/en/pricing) was 404/blocked to direct fetch — treat as vendor-cached, not independently re-verified today) |
| Haiku 4.5 output | **$5.00 / M tokens** | Same |
| Per report @ ~2k input / 300 output | (2,000×$1 + 300×$5)/1M = **$0.0035 ≈ ₹0.30** | Derived (estimate) |
| With Batch API (50% off, if latency allows) | ~₹0.15/report | Anthropic batch pricing, same reference |

**Per-report all-in AI cost (estimate):** text report **~₹0.30**;
voice report **~₹0.80–0.85** (₹0.30 extraction + ₹0.50 STT). Monthly:
~₹90–150 at 50 reports/week, **~₹350–700 at the 200/week ceiling** —
comfortably inside the ₹6/report the build plan budgets (see §8).

---

## 5. Map & tiles

| Option | Cost | Source (accessed 2026-08-04) |
|---|---|---|
| Self-hosted OpenStreetMap tiles (Wayside's plan) | **₹0** forever (own server serves the pilot zone's tiles) | project docs; no external dependency to price |
| **MapTiler** free tier (if real global hosted tiles are ever wanted) | **₹0 — 100,000 tile requests/mo**, 5,000 sessions, 100MB hosting; hard-stops (no surprise bills); paid Flex from $25/mo | [MapTiler pricing](https://www.maptiler.com/cloud/pricing/); [PricingNow](https://pricingnow.com/question/maptiler-cloud-pricing/) |
| **Stadia Maps** free tier | ₹0 for **non-commercial use** on a credit system (1 credit/raster tile), monthly hard limit; exact free-credit quota **not confirmed** in this research — check [docs.stadiamaps.com/limits](https://docs.stadiamaps.com/limits/) before relying on it | [Stadia pricing](https://stadiamaps.com/pricing/); [Stadia FAQs](https://stadiamaps.com/faqs/) |

**Conclusion:** self-hosted stays ₹0 and is the plan; MapTiler's 100k
free requests/month is a genuine, sourced fallback that a one-zone
pilot would not exhaust (a coordinator dashboard session uses tens to
hundreds of tile requests — estimate).

---

## 6. Domain and other pilot line items

| Item | Cost | Source (accessed 2026-08-04) |
|---|---|---|
| `.in` domain | **₹599 first year, ~₹800/yr renewal** (GoDaddy India) | [GoDaddy IN pricing](https://www.godaddy.com/en-in/pricing) via [Cybernews](https://cybernews.com/best-web-hosting/godaddy-review/pricing/); [ChennaiHost list ₹899](https://www.chennaihost.com/domains-price-list.html) |
| `.org` domain | **~₹750–1,400/yr** depending on registrar (SeekaHost ₹1,199; Namecheap cheapest per trackers) | [SeekaHost .org](https://www.seekahost.in/org-domain/); [TLD-List .org](https://tld-list.com/tld/org) |
| SIM for the public number | ~₹200–300/mo prepaid (estimate — ordinary Indian prepaid plan; not separately researched) | estimate |
| Telegram bot line | ₹0 | Telegram Bot API is free (well-established; no pricing page exists to cite) |
| WhatsApp Business verification / display name | ₹0 from Meta (BSPs sometimes charge setup fees — another reason to go direct) | [2Factor guide](https://2factor.in/v3/lp/whatsapp-business-api-pricing.php) |
| TLS certificates | ₹0 (Let's Encrypt / platform-issued) | standard practice; estimate |
| Geocoding | ₹0 at pilot volume on free tiers (per build-plan §2's 10k/month free lookup claim — **not re-verified in this pass**; flagging for a future check) | project doc |

---

## 7. Bottom line — monthly pilot run-rate (tech only, INR)

| Line | Low (lean, ~50/wk, Telegram-first, free credits active) | Realistic (~50/wk, WhatsApp live, 1GB machine) | High (200/wk ceiling, dashboard container, buffers) |
|---|---|---|---|
| Hosting (Fly.io Mumbai + volume + egress) | ₹300 | ₹550 | ₹1,100 |
| WhatsApp (Meta direct, utility msgs only) | ₹0 | ₹100 | ₹250 |
| Speech-to-text (Sarvam) | ₹0 (free credits) | ₹100 | ₹250 |
| AI extraction (Haiku 4.5) *(deployment-time)* | ₹100 | ₹150 | ₹700 |
| Domain (annualised ₹800–1,400) | ₹70 | ₹100 | ₹120 |
| SIM + misc | ₹0 | ₹250 | ₹350 |
| Contingency (~25% on the high case) | — | — | ₹700 |
| **Total / month** | **≈ ₹500** | **≈ ₹1,250** | **≈ ₹3,500** |

Every row above is derived from the sourced unit prices in §§1–6;
the volume assumptions (reports/week, voice-note share, notification
count) are estimates and stated where used. Even the high case is
**well under the ₹7,000–8,000 ceiling** the project's own cost doc
budgets — the published budget has real slack in it, which is the
right direction for a funder-facing number.

---

## 8. Deltas vs `research/cost-breakdown.md` (not edited)

1. **AI per report — doc is ~7–10× conservative.** Cost doc (§2, from
   build-plan §7) uses **~₹6/report** all-in → ₹5,200/mo at ceiling.
   Researched 2026 prices give **~₹0.30 (text) to ~₹0.85 (voice)** per
   report → ~₹350–700/mo at ceiling. The doc's figure is safe as a
   ceiling but overstates the AI line by roughly an order of magnitude
   at current Haiku 4.5 + Sarvam prices.
2. **Monthly tech total.** Doc: ₹3,000–4,000 realistic / ₹7,000–8,000
   ceiling. Research: **≈₹1,250 realistic / ≈₹3,500 ceiling.** Doc is
   comfortably conservative; no line researched came out *higher* than
   the doc's band.
3. **Hosting band confirmed.** Doc's ₹450–1,300 lean band matches
   sourced Fly.io prices ($3.19–$5.70/machine ≈ ₹280–500 + volume +
   India egress at $0.12/GB — the egress premium for Mumbai is a real
   but tiny line the doc doesn't itemise). One correction of emphasis:
   **Fly.io no longer has any free tier**, so the floor is paid from
   day one.
4. **WhatsApp line confirmed, with one nuance.** Doc's ~₹150–300/mo and
   ₹0.115/utility figure match 2026 Meta India rates. Nuance the doc
   predates: Meta's pricing became **per delivered message on
   2025-07-01** (doc's framing already reflects the free service
   window, so no material change), and the old "free monthly tier" of
   1,000 conversations was superseded — the free thing now is
   *unlimited service conversations*, which is even better for
   Wayside's inbound-heavy pattern. Doc's "Meta's free monthly tier
   covers a pilot's volume" phrasing is therefore slightly dated but
   directionally right. Marketing-rate increase of 2026-01-01
   (₹0.7846→₹0.8631) is irrelevant — Wayside sends no marketing
   messages.
5. **Maps ₹0 confirmed**, and strengthened: if self-hosting ever
   becomes a burden, MapTiler's sourced 100k-requests/month free tier
   covers pilot volume with zero spend.
6. **Domain range confirmed.** Doc's ₹800–2,000/yr contains the
   researched ₹599–1,400/yr; a `.in` at GoDaddy is at the bottom of
   the doc's band.
7. **Not in the doc / flagged:** Twilio-style BSPs would add
   ₹1,500–4,500/mo — the doc's implicit Meta-direct choice is worth
   making explicit; geocoding free-tier claim (10k/mo) was not
   re-verified here; Sarvam's ₹1,000 free credits and Saarika→Saaras v3
   deprecation are new facts the deployment-time integration should
   note.

*Research performed 2026-08-04 with web search from a proxied
environment; fly.io, docs.sarvam.ai, aisensy.com and
platform.claude.com pricing pages refused direct fetches (403/404), so
those figures rest on vendor-page search snippets corroborated by at
least one independent 2026 tracker each, as cited inline. Anthropic
Haiku 4.5 rates come from Anthropic's own developer reference bundle
(cached 2026-06-24). No paywalled numbers were guessed.*
