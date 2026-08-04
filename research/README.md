# Street Aid — research

Working name for the concept: spot people on the street who need basic medical supplies or weather protection, and get a funded aid kit to them fast using existing delivery infrastructure and NGO material flows (Goonj).

| Doc | What it is |
|---|---|
| [plan-options.md](./plan-options.md) | Summarised findings + three plan versions (Supply Line / Signal Loop / Aid Drops) and the recommended sequence |
| [plan-deep-dive.md](./plan-deep-dive.md) | Each plan in full operational detail, with the same worked example (the man with the injured foot) run through all three |
| [solo-buildability.md](./solo-buildability.md) | How far Versions B and C can be built independently before any pitch — component ledgers, walls, simulations, pitch sequencing |
| [goonj-pitch.md](./goonj-pitch.md) | 5-line pitch to Goonj for the Signal Loop pilot |
| [kevin-xu-proposal.md](./kevin-xu-proposal.md) | Full proposal ("Pukaar") for the Kevin Xu Innovation Challenge — fill the [bracketed] personal details before submitting |
| [build-plan.md](./build-plan.md) | Technical build plan v1 — evidence-locked stack decisions, component specs, life-of-a-case flow, DPDP mapping, costs, phased roadmap, open questions |
| [landscape-findings.md](./landscape-findings.md) | What already exists — products, city pilots, NGO/delivery programs, open-source repos — with sources |
| [critique-and-scope.md](./critique-and-scope.md) | Holes in the original plan, what survives, and a scoped 90-day MVP |
| [deep-research-prompt.md](./deep-research-prompt.md) | Copy-paste prompt to re-run this research in Claude (web search / Research mode) |
| [pitch/](./pitch/) | Kevin Xu Innovation Challenge pitch deck ("Wayside") — pptx, a plain-text version, and the generator script |
| [session-log.md](./session-log.md) | Running handoff log of what's built, decided, and still open — start here after a break or on a new machine |
| [product-plan.md](./product-plan.md) | The v1 build plan in non-technical language — six phases, each ending in something you can open and click |

Origin: seen on the street — a homeless man with a wrapped, bleeding foot; ~₹200 of antiseptic, dressings and an umbrella would have changed his week.

**The demo exists.** [`../pukaar/`](../pukaar/) implements the whole loop from the build plan — trilingual WhatsApp-style intake agent, deterministic 112 gate, kit orders with code-enforced caution, GoodSAM-style dispatch, provenance, retention — plus a recordable live control room (`make demo`), a metrics/kill-criteria dashboard, a standalone responder phone app at
`/responder` (an installable mobile app with push notifications), a
standalone witness page at `/witness`, a supervisor view at `/supervisor`,
a kit-depot network, and 184 automated tests (hardened by an adversarial
audit). See [`../pukaar/README.md`](../pukaar/README.md) and [`../pukaar/CHANGELOG.md`](../pukaar/CHANGELOG.md).
