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

---

## Final pre-demo checklist (added overnight, r11)

**Before you leave the house**
1. `git pull` in your clone — ten overnight rounds shipped; you want
   commit `31ee9657d` or later. Then `cd pukaar` and run
   `.venv/bin/python -m pytest -q` once: 224 passed = you're on the
   right build.
2. Boot with **no flags**: `.venv/bin/python -m pukaar` — the calm
   board IS the pitch mode. (`PUKAAR_SEED_DEMO=1` is only for the busy
   self-running showcase.)
3. Hard-refresh every open tab once (Cmd+Shift+R) so the newest static
   assets load.

**The three-screen setup**
- Laptop: control room at `http://127.0.0.1:8877/`.
- Your phone: `/responder` — pick Meena, ON DUTY.
- Second phone (or window): `/witness`.
- Same-wifi phones: start with `PUKAAR_HOST=0.0.0.0` and use
  `http://<laptop-ip>:8877/...` (find the ip: `ipconfig getifaddr en0`).

**Mid-demo instincts**
- Travel time compresses itself (⏩ in the clock) and hands back your
  speed on arrival — you don't need to touch the dropdown.
- The golden button works on a cold board — it brings a medical rider
  on shift by itself.
- If a job ever looks stuck: open the case → "release & re-wave". It
  stands the rider down honestly and re-offers; never close with a fake
  outcome.
- The closer: ▦ 90-day cells, then the purge (it asks first now).

**After the demo**
- If you used your API key anywhere, rotate it at
  console.anthropic.com → API Keys. It exists only in your shell env —
  keep it that way.
