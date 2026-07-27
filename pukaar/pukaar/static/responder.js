/* Pukaar responder app — the field worker's side of the marketplace.
   Drives the SAME API the sim uses: /api/state (poll), /api/manual (duty),
   /api/responder (accept / decline / outcome). Movement + arrival stay with
   the sim engine, so accepting here makes "you" drive across the map in the
   control room. */

const $ = (id) => document.getElementById(id);
const J = (s, d) => { try { return JSON.parse(s) ?? d; } catch { return d; } };
const CAT_ICON = { medical: "🩹", food: "🍚", shelter: "🌧️" };
const R = 6371000;

function haversineM(la1, lo1, la2, lo2) {
  const p = Math.PI / 180;
  const a = Math.sin(((la2 - la1) * p) / 2) ** 2 +
    Math.cos(la1 * p) * Math.cos(la2 * p) * Math.sin(((lo2 - lo1) * p) / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

let state = null;
let myId = localStorage.getItem("pukaar_resp") || "";
let pickFilled = false;
const seenOffers = new Set();
const startDist = new Map();   // order_id -> distance at accept (progress bar)
let audioCtx = null;

function beep(freq = 880, dur = 0.12) {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") return;
    const o = audioCtx.createOscillator(), g = audioCtx.createGain();
    o.frequency.value = freq; o.connect(g); g.connect(audioCtx.destination);
    g.gain.setValueAtTime(0.08, audioCtx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + dur);
    o.start(); o.stop(audioCtx.currentTime + dur);
  } catch { /* sound is optional */ }
}
document.addEventListener("pointerdown", () => {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    audioCtx.resume();
  } catch { /* ignore */ }
}, { once: true });

async function api(path, body) {
  const r = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}

function me() {
  return state ? state.sim.responders.find((r) => r.id === myId) || null : null;
}

function show(id) {
  for (const s of ["scr-pick", "scr-idle", "scr-offers", "scr-active"]) {
    $(s).hidden = s !== id;
  }
}

function toast(txt) {
  const t = $("toast");
  t.textContent = txt;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 1600);
}

/* ------------------------------------------------------------ screens -- */

function renderPick() {
  if (!pickFilled && state.sim.responders.length) {
    $("pick").innerHTML = state.sim.responders
      .map((r) => `<option value="${r.id}">${r.name}${r.medical ? " · medical-trained" : ""}</option>`)
      .join("");
    if (myId) $("pick").value = myId;
    pickFilled = true;
  }
  show("scr-pick");
}

function renderIdle(m) {
  offersKey = activeKey = "";
  const kits = state.metrics.kits || {};
  $("kits").innerHTML = Object.entries(kits)
    .map(([sku, n]) => `<span>${(state.kit_skus[sku] || {}).name || sku}: <b>${n}</b></span>`)
    .join("");
  const mine = state.orders.filter(
    (o) => o.responder_id === myId && (o.status === "closed" || o.status === "escalated"));
  $("me-stats").textContent =
    `${m.name} · ${mine.length} order${mine.length === 1 ? "" : "s"} closed this session` +
    (state.sim.is_night ? " · 🌙 night — dispatch resumes 07:00" : "");
  show("scr-idle");
}

function offerCard(a, order, c) {
  const m = me();
  const dist = c && c.lat != null && m
    ? `${Math.round(haversineM(m.lat, m.lng, c.lat, c.lng))} m` : "—";
  const ttl = (state.config && state.config.offer_ttl_s) || 180;
  const left = Math.max(0, a.offered_at + ttl - state.sim.sim_now);
  const kit = (state.kit_skus[order.sku] || {}).name || order.sku;
  return `<div class="card offer ${order.priority === "P1" ? "p1" : ""}" data-aid="${a.id}">
    <div class="row1">
      <span class="pill ${order.priority === "P1" ? "p1" : "p2"}">${order.priority}</span>
      <span class="kit">${CAT_ICON[c && c.category] || "•"} ${kit}</span>
    </div>
    <div class="meta"><span>📍 ${dist}</span><span>${c ? c.digipin || "" : ""}</span>
      <span>wave ${order.wave || 1}</span>${order.clinical_flag ? "<span>🩺 clinical flag</span>" : ""}</div>
    <div class="ttl" aria-label="time left to accept"><i style="width:${(left / ttl) * 100}%"></i></div>
    <div class="btnrow">
      <button class="big" data-acc="${a.id}">ACCEPT · ${Math.ceil(left / 60)} min left</button>
      <button class="big decline" data-dec="${a.id}">Pass</button>
    </div>
  </div>`;
}

let offersKey = "";
function renderOffers(offers) {
  const scr = $("scr-offers");
  const key = offers.map(({ a, order }) => `${a.id}:${order.status}`).join("|");
  if (key === offersKey && !scr.hidden) {
    // Same cards — refresh only the countdowns, IN PLACE, so a button is
    // never destroyed under the responder's finger mid-tap.
    const ttl = (state.config && state.config.offer_ttl_s) || 180;
    for (const { a } of offers) {
      const card = scr.querySelector(`[data-aid="${a.id}"]`);
      if (!card) continue;
      const left = Math.max(0, a.offered_at + ttl - state.sim.sim_now);
      const bar = card.querySelector(".ttl i");
      if (bar) bar.style.width = `${(left / ttl) * 100}%`;
      const acc = card.querySelector("[data-acc]");
      if (acc && !acc.disabled) acc.textContent = `ACCEPT · ${Math.ceil(left / 60)} min left`;
    }
    return;
  }
  offersKey = key;
  activeKey = "";
  scr.innerHTML = offers.map(({ a, order, c }) => offerCard(a, order, c)).join("");
  scr.querySelectorAll("[data-acc]").forEach((b) =>
    b.addEventListener("click", async () => {
      b.disabled = true;
      const res = await api("/api/responder", { action: "accept", assignment_id: b.dataset.acc });
      toast(res.ok ? "✓ accepted — head to the pin" : "offer already taken");
    }));
  scr.querySelectorAll("[data-dec]").forEach((b) =>
    b.addEventListener("click", () => {
      b.disabled = true;
      api("/api/responder", { action: "decline", assignment_id: b.dataset.dec });
    }));
  show("scr-offers");
}

let activeKey = "";
function renderActive(order) {
  const m = me();
  const c = state.cases.find((x) => x.id === order.case_id);
  const kit = state.kit_skus[order.sku] || { name: order.sku, contents: "" };
  const dist = c && c.lat != null && m ? haversineM(m.lat, m.lng, c.lat, c.lng) : null;
  if (order.status === "accepted" && dist != null && !startDist.has(order.id)) {
    startDist.set(order.id, Math.max(dist, 1));
  }
  const pct = dist != null && startDist.has(order.id)
    ? Math.max(0, Math.min(100, 100 - (dist / startDist.get(order.id)) * 100)) : 0;
  const onsite = order.status === "onsite";
  const key = `${order.id}:${order.status}`;
  if (key === activeKey && !$("scr-active").hidden) {
    // Same order & phase: move the distance readout and progress bar in
    // place; never rebuild the DOM under the outcome buttons.
    if (!onsite) {
      const d = $("scr-active").querySelector(".dist");
      if (d) d.innerHTML = `${dist != null ? Math.round(dist) : "—"}<small> m to go</small>`;
      const bar = $("scr-active").querySelector(".bar i");
      if (bar) bar.style.width = `${pct}%`;
    }
    return;
  }
  activeKey = key;
  offersKey = "";
  const checklist = kit.contents
    ? `<ul class="check">${kit.contents.split(", ").map((x) => `<li>${x}</li>`).join("")}</ul>` : "";
  const instr = J(order.instruction_ids, [])
    .map((i) => `<li>${state.instructions[i] || i}</li>`).join("");
  $("scr-active").innerHTML = `
    <div class="banner ${onsite ? "onsite" : "enroute"}">${onsite ? "AT THE PIN" : "EN ROUTE"}</div>
    <div class="card">
      <h2>Case ${order.case_id.slice(-4).toUpperCase()} · ${order.priority}</h2>
      <div class="digipin">${c ? c.digipin || "—" : "—"}</div>
      ${onsite
        ? `<p class="hint">You're on site. Give what's needed, then record what happened —
           the witness gets the closure message automatically.</p>`
        : `<div class="dist">${dist != null ? Math.round(dist) : "—"}<small> m to go</small></div>
           <div class="bar"><i style="width:${pct}%"></i></div>
           <p class="hint">Arrival is automatic when you reach the pin — watch yourself
           move on the <a href="/" target="_blank">control room map</a>.</p>`}
    </div>
    <div class="card">
      <h2>${CAT_ICON[c && c.category] || ""} ${kit.name} (${order.sku})</h2>
      ${checklist}
      ${order.clinical_flag ? '<p class="hint">🩺 clinical flag — medical escalation pre-approved.</p>' : ""}
    </div>
    ${instr ? `<div class="card"><h2>On arrival</h2><ol class="instr">${instr}</ol></div>` : ""}
    ${onsite ? `
    <div class="outgrid">
      <button class="big served" data-out="served">🟢 Help given</button>
      <button class="big escal" data-out="escalated">🩺 Call medical</button>
      <button class="big plain" data-out="not_found">Not found</button>
      <button class="big plain" data-out="declined">Declined help</button>
    </div>` : ""}`;
  $("scr-active").querySelectorAll("[data-out]").forEach((b) =>
    b.addEventListener("click", async () => {
      b.disabled = true;
      const res = await api("/api/responder",
        { action: "outcome", order_id: order.id, outcome: b.dataset.out });
      if (res.ok) { toast("✓ outcome recorded"); startDist.delete(order.id); }
    }));
  show("scr-active");
}

/* --------------------------------------------------------------- main -- */

function render() {
  if (!state) return;
  $("clock").textContent = state.sim.clock;
  const m = me();
  const onDuty = !!(m && m.manual);
  $("duty-pill").textContent = onDuty ? `on duty · ${m.name}` : "off duty";
  $("duty-pill").classList.toggle("on", onDuty);
  if (!onDuty) { renderPick(); return; }

  const active = state.orders.find(
    (o) => o.responder_id === myId && (o.status === "accepted" || o.status === "onsite"));
  if (active) { renderActive(active); return; }

  const byOrder = Object.fromEntries(state.orders.map((o) => [o.id, o]));
  const offers = state.assignments
    .filter((a) => a.responder_id === myId && !a.responded_at)
    .map((a) => ({ a, order: byOrder[a.order_id] }))
    .filter((x) => x.order && x.order.status === "offered")
    .map((x) => ({ ...x, c: state.cases.find((c) => c.id === x.order.case_id) }));
  for (const { a } of offers) {
    if (!seenOffers.has(a.id)) { seenOffers.add(a.id); beep(988); beep(784); }
  }
  if (offers.length) { renderOffers(offers); return; }
  renderIdle(m);
}

async function poll() {
  try {
    state = await (await fetch("/api/state")).json();
    $("f-status").textContent = "live";
    render();
  } catch {
    $("f-status").textContent = "reconnecting…";
  }
}

$("duty-btn").addEventListener("click", async () => {
  myId = $("pick").value;
  localStorage.setItem("pukaar_resp", myId);
  await api("/api/manual", { responder_id: myId, manual: true });
  await poll();
});

$("duty-off").addEventListener("click", async () => {
  await api("/api/manual", { responder_id: myId, manual: false });
  await poll();
});

poll();
setInterval(poll, 1000);
