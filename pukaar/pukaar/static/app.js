/* Pukaar control room — polls /api/state and renders the live world. */
"use strict";

const CAT = { medical: "#3987e5", food: "#d95926", shelter: "#199e70" };
const CAT_ICON = { medical: "🩹", food: "🍚", shelter: "🌧️" };
const OUTCOME_TXT = {
  served: ["🟢", "served", "good"], escalated: ["🩺", "served + clinical escalation", "good"],
  not_found: ["🟡", "not found", "warn"], declined: ["🟡", "declined help", "warn"],
};

let state = null, map, zoneCircle, witnessPin = null, selectedCase = null, wired = false;
const caseMarkers = new Map(), respMarkers = new Map(), routeLines = new Map();
let activeConv = "+91-DEMO";
const seenFeed = new Set();

// ------------------------------------------------------------------ map --
function initMap(zone) {
  map = L.map("map", { zoomControl: false, attributionControl: true })
    .setView([zone.lat, zone.lng], 15);
  L.control.zoom({ position: "bottomright" }).addTo(map);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
  }).addTo(map);
  zoneCircle = L.circle([zone.lat, zone.lng], {
    radius: zone.radius_m, color: "#898781", weight: 1.2, dashArray: "6 7",
    fill: false, opacity: 0.7,
  }).addTo(map);
  map.on("click", (e) => placeWitnessPin(e.latlng.lat, e.latlng.lng));
}

function placeWitnessPin(lat, lng) {
  if (!witnessPin) {
    witnessPin = L.marker([lat, lng], {
      draggable: true,
      icon: L.divIcon({ className: "", html: '<div class="witness-pin">📍</div>', iconAnchor: [11, 22] }),
    }).addTo(map);
  } else witnessPin.setLatLng([lat, lng]);
}

function caseIcon(c) {
  const open = !["closed"].includes(c.status);
  const pulse = open && (c.urgency === "high") ? " pulse" : "";
  const cls = open ? "" : " closedc";
  const color = CAT[c.category] || "#898781";
  return L.divIcon({
    className: "",
    html: `<div class="case-pin${pulse}${cls}" style="background:${color};position:relative"></div>`,
    iconSize: [16, 16], iconAnchor: [8, 8],
  });
}

function respIcon(r) {
  return L.divIcon({
    className: "",
    html: `<div class="resp-marker ${r.state}">${r.name[0]}</div>`,
    iconSize: [22, 22], iconAnchor: [11, 11],
  });
}

function syncMap() {
  if (!map || map === "failed") return;
  const liveIds = new Set();
  for (const c of state.cases) {
    if (c.lat == null) continue;
    const closedLong = c.status === "closed" && state.sim.sim_now - (c.closed_at || 0) > 1800;
    if (closedLong) continue;
    liveIds.add(c.id);
    if (!caseMarkers.has(c.id)) {
      const m = L.marker([c.lat, c.lng], { icon: caseIcon(c) })
        .on("click", () => showDetail(c.id)).addTo(map);
      caseMarkers.set(c.id, m);
    } else {
      caseMarkers.get(c.id).setIcon(caseIcon(c));
    }
  }
  for (const [id, m] of caseMarkers) if (!liveIds.has(id)) { m.remove(); caseMarkers.delete(id); }

  const liveResp = new Set();
  for (const r of state.sim.responders) {
    liveResp.add(r.id);
    if (!respMarkers.has(r.id)) {
      respMarkers.set(r.id, L.marker([r.lat, r.lng], { icon: respIcon(r), zIndexOffset: 500 })
        .bindTooltip(r.name, { direction: "top", offset: [0, -10] }).addTo(map));
    } else {
      const m = respMarkers.get(r.id);
      m.setLatLng([r.lat, r.lng]);
      m.setIcon(respIcon(r));
    }
  }

  const liveLines = new Set();
  for (const r of state.sim.responders) {
    if (r.state !== "enroute" || !r.order_id) continue;
    const order = state.orders.find((o) => o.id === r.order_id);
    const c = order && state.cases.find((x) => x.id === order.case_id);
    if (!c || c.lat == null) continue;
    liveLines.add(r.id);
    const pts = [[r.lat, r.lng], [c.lat, c.lng]];
    if (!routeLines.has(r.id)) {
      routeLines.set(r.id, L.polyline(pts, {
        color: CAT[c.category] || "#fff", weight: 2, dashArray: "6 8", opacity: 0.85,
        className: "route-line",
      }).addTo(map));
    } else routeLines.get(r.id).setLatLngs(pts);
  }
  for (const [id, l] of routeLines) if (!liveLines.has(id)) { l.remove(); routeLines.delete(id); }
}

// ---------------------------------------------------------------- tiles --
function fmtDur(s) {
  if (s == null) return "—";
  return s < 90 ? `${Math.round(s)}s` : `${Math.round(s / 60)}m`;
}

function renderTiles() {
  const m = state.metrics;
  const kits = Object.entries(m.kits || {}).map(([k, v]) => `${k.split("-")[0]} ${v}`).join(" · ");
  const tiles = [
    ["open cases", m.open_cases, ""],
    ["served", m.served, m.escalated ? `${m.escalated} escalated 🩺` : ""],
    ["acceptance", m.acceptance_pct == null ? "—" : m.acceptance_pct + "%", "of offers"],
    ["accept time", fmtDur(m.median_accept_s), m.p90_accept_s ? `p90 ${fmtDur(m.p90_accept_s)}` : "sim-time"],
    ["kits left", kits || "—", "partner_1"],
  ];
  document.getElementById("tiles").innerHTML = tiles.map(([l, v, s]) =>
    `<div class="tile"><div class="t-label">${l}</div><div class="t-value">${v}</div>` +
    `<div class="t-sub">${s || "&nbsp;"}</div></div>`).join("");
}

// ----------------------------------------------------------------- feed --
function feedLine(e) {
  const t = new Date(0); // sim clock is seconds-from-day-0
  const hh = String(Math.floor((e.ts % 86400) / 3600)).padStart(2, "0");
  const mm = String(Math.floor((e.ts % 3600) / 60)).padStart(2, "0");
  const time = `${hh}:${mm}`;
  const short = (id) => (id || "").slice(-4).toUpperCase();
  const respName = (id) => (state.sim.responders.find((r) => r.id === id) || { name: id }).name;
  let cls = "", html = "";
  switch (e.kind) {
    case "case_created": {
      const icon = CAT_ICON[e.category] || "❓";
      html = `${icon} new case <b>${short(e.case_id)}</b> · ${e.category || "uncategorised"}`; break;
    }
    case "case_merged":
      html = `👥 witness #${e.witnesses} merged into <b>${short(e.case_id)}</b> (dedup)`; break;
    case "order_created":
      html = `📦 order ${e.sku} · <b>${e.priority}</b>${e.clinical_flag ? " · 🩺 clinical flag" : ""}`;
      if (e.priority === "P1") cls = "crit";
      break;
    case "wave_started":
      html = `📣 <b>${short(e.order_id)}</b> wave ${e.wave} → ${e.offered_to.map(respName).join(", ")}`; break;
    case "order_accepted":
      html = `✅ <b>${respName(e.responder_id)}</b> accepted ${short(e.order_id)} (wave ${e.wave}, ${fmtDur(e.accept_s)})`;
      cls = "good"; break;
    case "responder_arrived":
      html = `📍 <b>${respName(e.responder_id)}</b> reached the spot`; break;
    case "outcome": {
      const [ic, txt, c] = OUTCOME_TXT[e.outcome] || ["·", e.outcome, ""];
      html = `${ic} <b>${short(e.case_id)}</b> ${txt}`; cls = c; break;
    }
    case "escalation_complete":
      html = `🩺 clinical follow-up completed for <b>${short(e.case_id)}</b>`; cls = "good"; break;
    case "emergency_redirect":
      html = `🚨 emergency text → fixed 112 reply, no agent involved`; cls = "crit"; break;
    case "coordinator_alert":
      html = `⚠️ coordinator: order ${short(e.order_id)} — ${e.reason}`; cls = "warn"; break;
    case "coordinator_flag":
      html = `⚠️ flag: ${e.reason}`; cls = "warn"; break;
    case "purge":
      html = `🧹 retention purge — media ${e.media}, lat/lng ${e.latlng}, rows ${e.cases}`; break;
    default:
      html = e.kind;
  }
  return `<div class="fi ${cls}"><span class="t">${time}</span><span>${html}</span></div>`;
}

function renderFeed() {
  const el = document.getElementById("feed");
  el.innerHTML = state.feed.map(feedLine).join("");
}

// ---------------------------------------------------------------- cases --
function renderCases() {
  const el = document.getElementById("cases");
  const open = state.cases.filter((c) => c.status !== "closed").slice(0, 12);
  el.innerHTML = open.map((c) => {
    const chip = c.urgency === "high"
      ? '<span class="chip p1">P1</span>'
      : `<span class="chip st-${c.status}">${c.status}</span>`;
    const who = c.merged_witnesses > 1 ? ` · ${c.merged_witnesses} witnesses` : "";
    return `<div class="case-row" data-id="${c.id}">
      <span class="dot" style="background:${CAT[c.category] || "#898781"}"></span>
      <span class="cid">${c.id.slice(-4).toUpperCase()}</span>
      <span class="meta">${c.landmark_text || c.digipin || ""}${who}</span>${chip}</div>`;
  }).join("") || '<div class="fi"><span class="t"></span><span>none — quiet streets 🌙</span></div>';
  el.querySelectorAll(".case-row").forEach((row) =>
    row.addEventListener("click", () => showDetail(row.dataset.id)));
}

// --------------------------------------------------------------- detail --
function showDetail(caseId) {
  selectedCase = caseId;
  renderDetail();
  const c = state.cases.find((x) => x.id === caseId);
  if (c && c.lat != null && map && map !== "failed") map.panTo([c.lat, c.lng]);
}

function renderDetail() {
  const panel = document.getElementById("detail-panel");
  if (!selectedCase) { panel.hidden = true; return; }
  const c = state.cases.find((x) => x.id === selectedCase);
  if (!c) { panel.hidden = true; return; }
  panel.hidden = false;
  document.getElementById("detail-id").textContent = c.id.slice(-4).toUpperCase();
  const order = state.orders.find((o) => o.case_id === c.id);
  const asgs = state.assignments.filter((a) => order && a.order_id === order.id);
  const respName = (id) => (state.sim.responders.find((r) => r.id === id) || { name: id || "—" }).name;

  const kv = `<div class="kv">
    <div>category</div><div>${CAT_ICON[c.category] || ""} ${c.category || "—"} ${c.urgency === "high" ? "· <b style='color:var(--critical)'>P1 ⚠</b>" : ""}</div>
    <div>DIGIPIN</div><div>${c.digipin || "—"}</div>
    <div>witnesses</div><div>${c.merged_witnesses}${c.merged_witnesses > 1 ? " (deduped)" : ""}</div>
    <div>detail</div><div>${(c.detail || c.landmark_text || "—").slice(0, 70)}</div>
    <div>kit</div><div>${order ? order.sku : "—"}${order && order.clinical_flag ? " · 🩺 clinical flag" : ""}</div>
    <div>provenance</div><div>witness ✓ / agent_inferred ✓ (HMAC)</div>
  </div>`;

  const steps = [];
  steps.push({ t: c.created_at, txt: "reported by witness", done: true });
  if (order) steps.push({ t: order.created_at, txt: `order ${order.sku} · ${order.priority} (${order.created_by})`, done: true });
  for (const a of asgs) {
    if (a.response === "accepted")
      steps.push({ t: a.responded_at, txt: `accepted by ${respName(a.responder_id)}`, done: true });
  }
  if (order && order.arrived_at) steps.push({ t: order.arrived_at, txt: `${respName(order.responder_id)} on site`, done: true });
  if (c.status === "closed" || c.status === "escalated") {
    steps.push({ t: order ? order.closed_at : c.closed_at, txt: c.status === "escalated" ? "served — clinical follow-up pending" : "closed", done: true });
  } else if (order && order.status === "offered") {
    steps.push({ t: null, txt: `wave ${order.wave} out — waiting for accept`, done: false });
  } else if (order && order.status === "needs_coordinator") {
    steps.push({ t: null, txt: "with human coordinator", done: false });
  }
  const tfmt = (t) => t == null ? "…" : `${String(Math.floor((t % 86400) / 3600)).padStart(2, "0")}:${String(Math.floor((t % 3600) / 60)).padStart(2, "0")}`;
  const tl = `<div class="timeline">` + steps.map((s) =>
    `<div class="tl ${s.done ? "done" : ""}"><div class="tl-t">${tfmt(s.t)}</div>${s.txt}</div>`).join("") + `</div>`;
  document.getElementById("detail-body").innerHTML = kv + tl;
}

// ---------------------------------------------------------------- phone --
function renderPhone() {
  const sel = document.getElementById("conv-select");
  const phones = Object.keys(state.conversations);
  if (!phones.includes(activeConv) && !phones.includes("+91-DEMO")) {
    // keep DEMO as an always-available local conversation
  }
  const options = Array.from(new Set(["+91-DEMO", ...phones]));
  sel.innerHTML = options.map((p) => `<option ${p === activeConv ? "selected" : ""}>${p}</option>`).join("");
  document.getElementById("conv-phone").textContent = activeConv;

  const log = (state.conversations[activeConv] || localLog);
  const msgs = document.getElementById("msgs");
  const atBottom = msgs.scrollHeight - msgs.scrollTop - msgs.clientHeight < 60;
  msgs.innerHTML = log.map((m) => {
    const who = m.from === "bot" ? "bot" : "witness";
    return `<div class="bubble ${who}">${escapeHtml(m.text)}<span class="b-meta">${who === "bot" ? "Pukaar" : "you"}</span></div>`;
  }).join("");
  if (atBottom) msgs.scrollTop = msgs.scrollHeight;

  const last = log.length ? log[log.length - 1] : null;
  const quick = document.getElementById("quick");
  if (last && last.from === "bot" && last.buttons && last.buttons.length) {
    quick.innerHTML = last.buttons.map((b) =>
      `<button data-payload="${b.id}">${b.label}</button>`).join("");
    quick.querySelectorAll("button").forEach((btn) =>
      btn.addEventListener("click", () => sendInbound("button", { text: btn.dataset.payload })));
  } else quick.innerHTML = "";
}

const localLog = []; // demo conversation before the server knows it
function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

async function sendInbound(kind, extra = {}) {
  const body = { phone: activeConv, kind, ...extra };
  if (kind === "text" || kind === "button") {
    localEcho(extra.text, kind);
  }
  const res = await fetch("/api/wa/inbound", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  await res.json();
  await refresh(); // pull the authoritative conversation immediately
}

function localEcho(text, kind) {
  if (!state || !state.conversations[activeConv]) {
    localLog.push({ from: "witness", kind, text, buttons: [] });
  }
}

// ---------------------------------------------------------------- wires --
function wire() {
  document.getElementById("btn-send").addEventListener("click", sendText);
  document.getElementById("msg-in").addEventListener("keydown", (e) => { if (e.key === "Enter") sendText(); });
  document.getElementById("btn-loc").addEventListener("click", () => {
    let lat, lng;
    if (witnessPin) ({ lat, lng } = witnessPin.getLatLng());
    else {
      const z = state.zone;
      lat = z.lat + (Math.random() - 0.5) * 0.012; lng = z.lng + (Math.random() - 0.5) * 0.012;
      if (map && map !== "failed") placeWitnessPin(lat, lng);
    }
    sendInbound("location", { lat, lng });
  });
  document.getElementById("btn-photo").addEventListener("click", () =>
    sendInbound("photo", { photo_hint: "street photo: person with a bandaged foot, blood visible, sitting on pavement" }));
  document.getElementById("conv-select").addEventListener("change", (e) => {
    activeConv = e.target.value; renderPhone();
  });
  document.querySelectorAll(".scenarios button").forEach((b) =>
    b.addEventListener("click", async () => { await fetch(`/api/scenario/${b.dataset.sc}`, { method: "POST" }); refresh(); }));
  document.getElementById("btn-pause").addEventListener("click", async () => {
    const action = state.sim.running ? "pause" : "resume";
    await fetch("/api/sim", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action }) });
    refresh();
  });
  document.getElementById("speed").addEventListener("change", async (e) => {
    await fetch("/api/sim", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: "speed", value: +e.target.value }) });
  });
  document.getElementById("btn-purge").addEventListener("click", async () => { await fetch("/api/purge", { method: "POST" }); refresh(); });
  document.getElementById("detail-close").addEventListener("click", () => { selectedCase = null; renderDetail(); });
}

function sendText() {
  const input = document.getElementById("msg-in");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  sendInbound("text", { text });
}

// ----------------------------------------------------------------- loop --
async function refresh() {
  try {
    const res = await fetch("/api/state");
    state = await res.json();
  } catch { return; }
  if (!wired) { wire(); wired = true; }
  if (!map) {
    try { initMap(state.zone); } catch (err) {
      // Leaflet missing or map failure must never take the panels down.
      document.getElementById("map").innerHTML =
        '<div style="display:grid;place-items:center;height:100%;color:#898781">map unavailable — data panels live</div>';
      map = "failed";
    }
  }
  document.getElementById("clock").textContent = `${state.sim.clock} · ${state.sim.speed}×`;
  document.getElementById("btn-pause").textContent = state.sim.running ? "⏸" : "▶";
  const speedSel = document.getElementById("speed");
  if ([...speedSel.options].some((o) => +o.value === state.sim.speed)) speedSel.value = String(state.sim.speed);
  const badge = document.getElementById("backend-badge");
  badge.textContent = state.backend === "claude" ? "CLAUDE LIVE" : "MOCK AGENT";
  badge.classList.toggle("live", state.backend === "claude");
  document.getElementById("foot-backend").textContent = state.backend;
  document.getElementById("prov-note").textContent =
    state.prov_ephemeral ? "demo HMAC key (ephemeral) — set PUKAAR_HMAC_KEY for persistent provenance" : "persistent HMAC provenance key";
  syncMap(); renderTiles(); renderFeed(); renderCases(); renderPhone(); renderDetail();
}

refresh();
setInterval(refresh, 1000);
