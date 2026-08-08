# Wayside — the 3-minute live demo script

For: pitching the working product (judges, NGO partners, CSR leads).
Setup beforehand, once: `make demo` on the laptop; `http://<laptop-ip>:8877/responder`
open on your phone (same Wi-Fi), pick **Meena**, tap **Go on duty**, allow
notifications. Keep the control room (`/`) on the projector and `/witness`
in a second tab. Sound on.

Every beat is: **what you do → what you say** (roughly 20 seconds each).
Nothing here depends on luck — the simulation keeps the world alive, and
beat 8 is the safety net.

---

**1 · The problem, on one screen** — *Control room already open.*
Say: "This is one square kilometre of Nizamuddin, Delhi. Every dot that
appears is a person someone walked past. The question Wayside answers:
what if seeing someone was enough?"

**2 · Report like a real witness** — *Switch to /witness. Type:*
`flyover ke neeche aadmi ghayal hai, khoon aa raha hai` *— then tap the
map to drop the pin, send it.*
Say: "A witness reports in the language they actually speak. No app, no
account — a chat and a pin. Watch what the system asks: it's filling the
slots a dispatcher needs, nothing more."

**3 · Triage to dispatch, live** — *Back to the control room. The case
pops in the feed; the wave goes out.*
Say: "Triage picked a medical kit, priority one. Offers just went to the
nearest trained responders — first to accept wins, exactly how real
emergency dispatch works at scale."

**4 · Your phone buzzes** — *Hold up the phone: the push notification,
then tap ACCEPT.*
Say: "That's a real push notification — the app was closed. I'm Meena
today. I accept…" *(show the screen)* "…and I get turn-by-turn street
directions, and — see this — I'm routed **via the depot** first, because
the kit lives at the NGO's shelf, not in my bag."

**5 · The map doesn't lie** — *Point at Meena's dot following streets;
the kit-pickup line appears in the feed.*
Say: "She walks the actual streets — no dot floating over rooftops. Kit
collected at the Basti Office; stock just decremented on that tile. If
she doesn't find the person, the kit goes back on the shelf. The ledger
survives even a server crash mid-delivery — we test that."

**6 · Close the loop** — *On the phone: I've arrived → choose the
outcome. Flip to /witness: the closure message has landed.*
Say: "The witness who cared enough to report gets told how it ended.
That's the loop: see it, send word, someone comes — and you know."

**7 · The privacy beat** — *Control room: tap the purge button, then the
90-day cells toggle.*
Say: "A map of where vulnerable people sleep must not exist. So it
doesn't: 72-hour case expiry, pins deleted on schedule, and after 90
days only these coarse cells survive. That retention job isn't a policy
document — I just ran it in front of you."

**8 · Safety nets (only if needed)**
- Anything goes sideways → tap **Golden run** in Scenarios: a guaranteed
  clean P1 arc through the real pipeline.
- Crowd wants the party trick → airplane mode on the phone, reopen the
  app: it still opens, kit checklist and all. "Streets don't come with
  good signal. We don't assume any."

---

**Numbers you may quote** (all measured or sourced, nothing invented):
217 automated tests · ~0.5 ms per route · kits ₹172 / ₹50 / ₹173
wholesale · ₹6,900 seeds three depots · ≈₹36,500 year-one stock ·
≈₹1,250/month realistic pilot run-rate.

**Do not claim:** any NGO partnership (conversations start with this
demo), real WhatsApp integration (the witness page IS the line today),
or surveyed map data (the geometry is representative; the import tool
for real OSM streets exists and is one command).
