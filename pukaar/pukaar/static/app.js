/* Pukaar control room — polls /api/state and renders the live world. */
"use strict";

const CAT = { medical: "#3987e5", food: "#d95926", shelter: "#199e70" };
const CAT_ICON = { medical: "🩹", food: "🍚", shelter: "🌧️" };
// monochrome map-pin glyphs (inline SVG, no emoji rendering variance on the map)
const CAT_GLYPH = {
  medical: '<svg viewBox="0 0 24 24" class="pin-glyph"><path d="M10 3.5h4V10h6.5v4H14v6.5h-4V14H3.5v-4H10z"/></svg>',
  food: '<svg viewBox="0 0 24 24" class="pin-glyph"><rect x="2.8" y="8.1" width="18.4" height="1.7" rx="0.85"/><path d="M3.6 10.4h16.8a8.4 8.4 0 0 1-16.8 0z"/></svg>',
  shelter: '<svg viewBox="0 0 24 24" class="pin-glyph"><path d="M12 4 4 11.4V20h16v-8.6z"/></svg>',
};
const OUTCOME_TXT = {
  served: ["🟢", "served", "good"], escalated: ["🩺", "served + clinical escalation", "good"],
  not_found: ["🟡", "not found", "warn"], declined: ["🟡", "declined help", "warn"],
};

let state = null, map, zoneCircle, witnessPin = null, selectedCase = null, wired = false;
const caseMarkers = new Map(), respMarkers = new Map(), routeLines = new Map();
const respTrails = new Map(), trailLines = new Map();   // responder movement trails
let followGolden = false;                                // 🎥 camera follows the golden run
let activeConv = "+91-DEMO";
let selectedResp = "resp_1";
let soundOn = false, audioCtx = null, lastFeedTs = -1;

const J = (v, fb) => { try { const x = typeof v === "string" ? JSON.parse(v) : v; return x ?? fb; } catch { return fb; } };

function haversineM(a, b, c, d) {
  const R = 6371000, r = Math.PI / 180;
  const x = Math.sin((c - a) * r / 2) ** 2 +
    Math.cos(a * r) * Math.cos(c * r) * Math.sin((d - b) * r / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(x));
}

// Monochrome toolbar icons (currentColor, inherit the button's hover/active color).
const ICON_BELL =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="ic"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>';
const ICON_BELL_OFF =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="ic"><path d="M13.73 21a2 2 0 0 1-3.46 0"/><path d="M18.63 13A17.89 17.89 0 0 1 18 8"/><path d="M6.26 6.26A5.86 5.86 0 0 0 6 8c0 7-3 9-3 9h14"/><path d="M18 8a6 6 0 0 0-9.33-5"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';

function updateFollowBtn() {
  // Toggle the .on class only — #btn-follow.on turns the SVG amber via currentColor.
  // (Don't set textContent: that would wipe the inline icon.)
  const b = document.getElementById("btn-follow");
  if (b) b.classList.toggle("on", followGolden);
}

// ---------------------------------------------------------------- sound --
function beep(freq, dur = 0.09, delay = 0, vol = 0.045, type = "sine") {
  if (!soundOn || !audioCtx) return;
  const t = audioCtx.currentTime + delay;
  const o = audioCtx.createOscillator(), g = audioCtx.createGain();
  o.type = type; o.frequency.value = freq;
  g.gain.setValueAtTime(vol, t);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.connect(g).connect(audioCtx.destination);
  o.start(t); o.stop(t + dur + 0.02);
}

function soundFor(e) {
  switch (e.kind) {
    case "order_accepted": beep(660); beep(880, 0.1, 0.1); break;
    case "outcome": if (e.outcome === "served" || e.outcome === "escalated") beep(523, 0.16, 0, 0.05); break;
    case "order_created": if (e.priority === "P1") { beep(220, 0.13, 0, 0.06, "square"); beep(220, 0.13, 0.18, 0.06, "square"); } break;
    case "coordinator_alert": beep(392, 0.2, 0, 0.05, "triangle"); break;
  }
}

function playNewFeedSounds() {
  if (!state) return;
  for (const e of [...state.feed].reverse()) {
    if (e.ts > lastFeedTs) soundFor(e);
  }
  if (state.feed.length) lastFeedTs = Math.max(lastFeedTs, ...state.feed.map((e) => e.ts));
}

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
  map.on("dragstart", () => { followGolden = false; updateFollowBtn(); });
}

function placeWitnessPin(lat, lng) {
  if (!witnessPin) {
    witnessPin = L.marker([lat, lng], {
      draggable: true,
      icon: L.divIcon({ className: "", html: '<div class="witness-pin">📍</div>', iconAnchor: [11, 22] }),
    }).addTo(map);
  } else witnessPin.setLatLng([lat, lng]);
}

// ------------------------------------------------------ smooth motion --
// The UI polls at 1 Hz, so raw positions arrive as 1-second jumps. Responder
// markers glide between polls via one rAF loop (their attached route line
// rides along). Reduced-motion users get instant snaps.
const REDUCED_MOTION = window.matchMedia
  && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const respTweens = new Map();   // id -> {m, from, to, start}
let tweenRaf = null;

function glideMarker(id, m, to) {
  if (REDUCED_MOTION || !map || map === "failed") { m.setLatLng(to); return; }
  const cur = m.getLatLng();
  if (cur.lat === to[0] && cur.lng === to[1]) { respTweens.delete(id); return; }
  respTweens.set(id, { m, from: [cur.lat, cur.lng], to, start: performance.now() });
  if (!tweenRaf) tweenRaf = requestAnimationFrame(tweenTick);
}

function tweenTick(now) {
  for (const [id, t] of respTweens) {
    const k = Math.min(1, (now - t.start) / 950);   // ~one poll interval
    const lat = t.from[0] + (t.to[0] - t.from[0]) * k;
    const lng = t.from[1] + (t.to[1] - t.from[1]) * k;
    t.m.setLatLng([lat, lng]);
    const line = routeLines.get(id);
    if (line) {
      const ll = line.getLatLngs();
      if (ll.length === 2) line.setLatLngs([[lat, lng], ll[1]]);
    }
    if (k >= 1) respTweens.delete(id);
  }
  tweenRaf = respTweens.size ? requestAnimationFrame(tweenTick) : null;
}

function caseIcon(c) {
  const open = !["closed"].includes(c.status);
  const pulse = open && (c.urgency === "high") ? " pulse" : "";
  const cls = open ? "" : " closedc";
  const color = CAT[c.category] || "#898781";
  const glyph = CAT_GLYPH[c.category] || "";
  return L.divIcon({
    className: "",
    html: `<div class="case-pin${pulse}${cls}" style="background:${color}">${glyph}</div>`,
    iconSize: [20, 20], iconAnchor: [10, 10],
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
      glideMarker(r.id, m, [r.lat, r.lng]);
      // swap the icon only on a state change — replacing the DOM node every
      // poll flickers and would cut any in-flight glide
      if (m.__stateKey !== r.state) { m.setIcon(respIcon(r)); m.__stateKey = r.state; }
    }
    // movement trail: keep the last ~24 points while working, fade otherwise
    const trail = respTrails.get(r.id) || [];
    const last = trail[trail.length - 1];
    if (!last || last[0] !== r.lat || last[1] !== r.lng) trail.push([r.lat, r.lng]);
    while (trail.length > 24) trail.shift();
    if (r.state === "idle" && trail.length > 2) trail.splice(0, 2);   // idle: trail evaporates
    respTrails.set(r.id, trail);
    if (trail.length > 1) {
      if (!trailLines.has(r.id)) {
        trailLines.set(r.id, L.polyline(trail, {
          color: "#e8e6df", weight: 2, opacity: 0.22, interactive: false }).addTo(map));
      } else trailLines.get(r.id).setLatLngs(trail);
    } else if (trailLines.has(r.id)) {
      trailLines.get(r.id).remove(); trailLines.delete(r.id);
    }
  }

  // 🎥 follow the golden run's responder while its order is live
  if (followGolden && (state.sim.golden || []).length) {
    const gid = state.sim.golden[state.sim.golden.length - 1];
    const order = state.orders.find((o) => o.id === gid);
    if (order && ["accepted", "onsite"].includes(order.status) && order.responder_id) {
      const r = state.sim.responders.find((x) => x.id === order.responder_id);
      if (r) map.panTo([r.lat, r.lng], { animate: true, duration: 0.8 });
    } else if (order && ["closed", "escalated"].includes(order.status)) {
      followGolden = false;   // arc over — release the camera
      updateFollowBtn();
    }
  }

  const liveLines = new Set();
  for (const r of state.sim.responders) {
    if (r.state !== "enroute" || !r.order_id) continue;
    const order = state.orders.find((o) => o.id === r.order_id);
    const c = order && state.cases.find((x) => x.id === order.case_id);
    if (!c || c.lat == null) continue;
    liveLines.add(r.id);
    // the route line starts at the MARKER's gliding position, not the raw
    // server position, so the line stays glued to the moving dot
    const mk = respMarkers.get(r.id);
    const mp = mk ? mk.getLatLng() : { lat: r.lat, lng: r.lng };
    const pts = [[mp.lat, mp.lng], [c.lat, c.lng]];
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
  const low = m.kits_low || [];
  // Same vocabulary as the responder app: one-word label from the shared
  // kit_skus name so "Monsoon"/"Medical"/"Food" read identically on both
  // surfaces (uppercased to keep the dense ops-tile look).
  const kitWord = (k) => (((state.kit_skus || {})[k] || {}).name || k).split(/[\s-]/)[0].toUpperCase();
  const kits = Object.entries(m.kits || {}).map(([k, v]) =>
    `${kitWord(k)} ${v}${low.includes(k) ? "⚠" : ""}`).join(" · ");
  const tiles = [
    ["open cases", m.open_cases, "", ""],
    ["served", m.served, m.escalated ? `${m.escalated} escalated 🩺` : "", ""],
    ["acceptance", m.acceptance_pct == null ? "—" : m.acceptance_pct + "%", "of offers", ""],
    ["accept time", fmtDur(m.median_accept_s), m.p90_accept_s ? `p90 ${fmtDur(m.p90_accept_s)}` : "sim-time", ""],
    ["kits left", kits || "—", low.length ? `⚠ low: ${low.map(kitWord).join(", ")} — restock en route` : "partner_1",
     low.length ? " low" : ""],
  ];
  const el = document.getElementById("tiles");
  const prev = el.__vals || {};
  const next = {};
  el.innerHTML = tiles.map(([l, v, s, cls]) => {
    next[l] = String(v);
    const bump = prev[l] !== undefined && prev[l] !== String(v) ? " bump" : "";
    return `<div class="tile${cls}"><div class="t-label">${l}</div>` +
      `<div class="t-value${bump}${l === "kits left" ? " kits" : ""}">${v}</div>` +
      `<div class="t-sub">${s || "&nbsp;"}</div></div>`;
  }).join("");
  el.__vals = next;
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
      html = `🧹 retention purge — media ${e.media}, lat/lng ${e.latlng}, rows ${e.cases}, orphan reports ${e.orphan_reports ?? 0}`; break;
    case "night_hold":
      html = `🌙 <b>${short(e.case_id)}</b> held for the morning round (night mode)`; cls = "warn"; break;
    case "manual_assign":
      html = `🧑‍✈️ coordinator assigned ${short(e.order_id)} → <b>${respName(e.responder_id)}</b>`; cls = "good"; break;
    case "restock_needed":
      html = `📦 ${e.sku} low (${e.count} left) — courier restock requested`; cls = "warn"; break;
    case "restock_delivered":
      html = `📦 courier delivered +${e.qty} × ${e.sku} to partner_1`; cls = "good"; break;
    case "recheck_sent":
      html = `🤔 asked the witness of <b>${short(e.case_id)}</b>: still there?`; break;
    case "recheck_confirmed":
      html = `✅ witness confirms <b>${short(e.case_id)}</b> — report refreshed`; cls = "good"; break;
    case "case_withdrawn":
      html = `🚪 <b>${short(e.case_id)}</b> closed — witness says the person moved on`; cls = "warn"; break;
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
      <span class="cat-ic" title="${escapeHtml(c.category || "")}">${CAT_ICON[c.category] || ""}</span>
      <span class="cid">${c.id.slice(-4).toUpperCase()}</span>
      <span class="meta">${escapeHtml(c.landmark_text || c.digipin || "")}${who}</span>${chip}</div>`;
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
    <div>detail</div><div>${escapeHtml((c.detail || c.landmark_text || "—").slice(0, 70))}</div>
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

// ------------------------------------------------------- responder phone --
function renderRespPanel() {
  const sel = document.getElementById("resp-select");
  sel.innerHTML = state.sim.responders.map((r) =>
    `<option value="${r.id}" ${r.id === selectedResp ? "selected" : ""}>${r.name}${r.medical ? " 🩺" : ""}</option>`).join("");
  const me = state.sim.responders.find((r) => r.id === selectedResp);
  document.getElementById("resp-manual").checked = !!(me && me.manual);

  const cards = [];
  const pending = state.assignments.filter((a) =>
    a.responder_id === selectedResp && a.responded_at == null);
  for (const a of pending) {
    const order = state.orders.find((o) => o.id === a.order_id && o.status === "offered");
    if (!order) continue;
    const c = state.cases.find((x) => x.id === order.case_id) || {};
    const dist = (me && c.lat != null) ? `${Math.round(haversineM(me.lat, me.lng, c.lat, c.lng))}m` : "—";
    const instr = J(order.instruction_ids, []).map((i) => `<li>${state.instructions[i] || i}</li>`).join("");
    cards.push(`<div class="rcard">
      <div class="r-head"><b>${CAT_ICON[c.category] || "📦"} ${order.sku} · ${order.priority}</b><span>${dist}</span></div>
      ${order.clinical_flag ? "🩺 clinical flag · " : ""}${escapeHtml((c.detail || c.landmark_text || "").slice(0, 60))}
      <ul class="r-instr">${instr}</ul>
      <div class="btns">
        <button class="accept" data-act="accept" data-asg="${a.id}">✅ Accept</button>
        <button class="decline" data-act="decline" data-asg="${a.id}">Decline</button>
      </div></div>`);
  }
  const active = state.orders.find((o) =>
    o.responder_id === selectedResp && ["accepted", "onsite", "escalated"].includes(o.status));
  if (active) {
    const c = state.cases.find((x) => x.id === active.case_id) || {};
    let statusTxt = { accepted: "🛵 en route", onsite: "📍 on site", escalated: "🩺 clinical follow-up pending" }[active.status];
    if (active.status === "accepted" && me && c.lat != null) {
      statusTxt += ` · ${Math.round(haversineM(me.lat, me.lng, c.lat, c.lng))}m`;
    }
    const outcomeBtns = active.status === "onsite" && me && me.manual ? `
      <div class="btns">
        <button class="accept" data-act="outcome" data-order="${active.id}" data-out="served">🟢 Diya</button>
        <button data-act="outcome" data-order="${active.id}" data-out="not_found">Nahi mila</button>
        <button data-act="outcome" data-order="${active.id}" data-out="declined">Mana kiya</button>
        <button data-act="outcome" data-order="${active.id}" data-out="escalated">🩺 Doctor bulao</button>
      </div>` : (active.status === "onsite" ? `<div class="r-instr">sim will close this — tick "I'm playing" to decide yourself</div>` : "");
    cards.push(`<div class="rcard"><div class="r-head"><b>${active.sku} · ${c.digipin || ""}</b><span>${statusTxt}</span></div>${outcomeBtns}</div>`);
  }
  document.getElementById("resp-cards").innerHTML =
    cards.join("") || '<div class="rcard idle">no offers right now — on patrol</div>';
  document.querySelectorAll("#resp-cards [data-act]").forEach((b) =>
    b.addEventListener("click", async () => {
      const body = b.dataset.act === "outcome"
        ? { action: "outcome", order_id: b.dataset.order, outcome: b.dataset.out }
        : { action: b.dataset.act, assignment_id: b.dataset.asg };
      await fetch("/api/responder", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (b.dataset.act === "outcome") flashRespToast("✓ outcome recorded");
      refresh();
    }));
}

let respToastUntil = 0;
function flashRespToast(text) {
  respToastUntil = Date.now() + 1600;
  let t = document.getElementById("resp-toast");
  if (!t) {
    t = document.createElement("div");
    t.id = "resp-toast";
    document.getElementById("resp-panel").appendChild(t);
  }
  t.textContent = text;
  t.hidden = false;
  setTimeout(() => { if (Date.now() >= respToastUntil) t.hidden = true; }, 1700);
}

// ------------------------------------------------------- coordinator ----
// nearest idle responder to a case — the "suggested assignee" preselected
// in the dropdown so the coordinator confirms one click instead of guessing
function nearestIdle(c) {
  if (c.lat == null) return null;
  let best = null, bestD = Infinity;
  for (const r of state.sim.responders) {
    if (r.state !== "idle") continue;
    const d = haversineM(r.lat, r.lng, c.lat, c.lng);
    if (d < bestD) { bestD = d; best = r; }
  }
  return best ? { id: best.id, m: Math.round(bestD) } : null;
}

function renderCoord() {
  const stuck = state.orders.filter((o) => o.status === "needs_coordinator");
  const panel = document.getElementById("coord-panel");
  panel.hidden = stuck.length === 0;
  document.getElementById("coord-count").textContent = stuck.length || "";
  if (!stuck.length) return;
  document.getElementById("coord-body").innerHTML = stuck.map((o) => {
    const c = state.cases.find((x) => x.id === o.case_id) || {};
    const pinless = c.lat == null;
    if (pinless) {
      // no pin -> can't route; the fix is to get one from the witness
      return `<div class="fi warn"><span class="t">${o.sku}</span>
        <span><b>${o.id.slice(-4).toUpperCase()}</b> 📍 landmark only — ${escapeHtml((c.landmark_text || c.detail || "").slice(0, 28))}</span>
        <span class="act"><button class="req-pin" data-case="${o.case_id}">request pin</button></span></div>`;
    }
    const sug = nearestIdle(c);
    const opts = state.sim.responders.map((r) => {
      const isSug = sug && r.id === sug.id;
      return `<option value="${r.id}" ${isSug ? "selected" : ""}>${r.name}${isSug ? ` · ${sug.m}m ★` : ""}</option>`;
    }).join("");
    return `<div class="fi warn"><span class="t">${o.sku}</span>
      <span><b>${o.id.slice(-4).toUpperCase()}</b> ${escapeHtml((c.detail || "").slice(0, 30))}</span>
      <span class="act"><select data-order="${o.id}">${opts}</select>
      <button class="accept" data-assign="${o.id}">assign</button></span></div>`;
  }).join("");
  document.querySelectorAll("#coord-body [data-assign]").forEach((b) =>
    b.addEventListener("click", async () => {
      const sel = document.querySelector(`#coord-body select[data-order="${b.dataset.assign}"]`);
      await fetch("/api/responder", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "assign", order_id: b.dataset.assign, responder_id: sel.value }),
      });
      refresh();
    }));
  document.querySelectorAll("#coord-body .req-pin").forEach((b) =>
    b.addEventListener("click", async () => {
      b.disabled = true; b.textContent = "asked ✓";
      await fetch("/api/coordinator/request_pin", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case_id: b.dataset.case }),
      });
    }));
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
  const bubbleTime = (ts) => {
    if (!ts) return "";
    const h = String(Math.floor((ts % 86400) / 3600)).padStart(2, "0");
    const mm = String(Math.floor((ts % 3600) / 60)).padStart(2, "0");
    return ` · ${h}:${mm}`;
  };
  // keyed render: rebuild only when the thread actually changed, and only
  // NEW bubbles animate in — no strobing, no per-second DOM churn
  const typing = typingUntil > Date.now();
  const threadKey = `${activeConv}:${log.length}:${log.length ? log[log.length - 1].ts : 0}:${typing}`;
  if (msgs.dataset.key !== threadKey) {
    const sameConv = msgs.dataset.conv === activeConv;
    const prevCount = sameConv ? +(msgs.dataset.count || 0) : Infinity;
    // empty thread opens with the aid-line greeting so the pane never boots hollow
    const greeting = log.length === 0 && !typing
      ? `<div class="bubble bot"><b>Hello 🙏 This is Pukaar</b> — report someone on the street who needs help. Pick a scenario or type to begin.<span class="b-meta">Pukaar</span></div>`
      : "";
    msgs.innerHTML = greeting + log.map((m, i) => {
      const who = m.from === "bot" ? "bot" : "witness";
      const fresh = i >= prevCount ? " fresh" : "";
      const voice = m.kind === "voice" ? ` voice" data-len="${3 + (m.text || "").length % 7}` : "";
      return `<div class="bubble ${who}${fresh}${voice}">${escapeHtml(m.text)}<span class="b-meta">${who === "bot" ? "Pukaar" : "you"}${bubbleTime(m.ts)}</span></div>`;
    }).join("") + (typing
      ? '<div class="bubble bot typing"><span></span><span></span><span></span></div>' : "");
    msgs.dataset.key = threadKey;
    msgs.dataset.conv = activeConv;
    msgs.dataset.count = String(log.length);
    if (atBottom) msgs.scrollTop = msgs.scrollHeight;
  }

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
let typingUntil = 0; // WhatsApp-style typing dots after the witness sends
function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

async function sendInbound(kind, extra = {}) {
  const body = { phone: activeConv, kind, ...extra };
  if (kind === "text" || kind === "button") {
    localEcho(extra.text, kind);
  } else if (kind === "voice") {
    localEcho("🎤 " + extra.text, "voice");
  }
  typingUntil = Date.now() + 900;          // brief typing dots feel human
  renderPhone();
  const res = await fetch("/api/wa/inbound", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  await res.json();
  setTimeout(() => { typingUntil = 0; refresh(); }, 700);
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
  const photoMenu = document.getElementById("photo-menu");
  document.getElementById("btn-photo").addEventListener("click", () => {
    photoMenu.hidden = !photoMenu.hidden;
  });
  photoMenu.querySelectorAll("button[data-hint]").forEach((b) =>
    b.addEventListener("click", () => {
      photoMenu.hidden = true;
      sendInbound("photo", { photo_hint: b.dataset.hint });
    }));
  const cellsBtn = document.getElementById("cells-toggle");
  cellsBtn.addEventListener("click", () => {
    cellsOn = !cellsOn;
    cellsBtn.classList.toggle("on", cellsOn);
    cellsBtn.setAttribute("aria-pressed", String(cellsOn));
    drawCells();
  });
  const VOICE_SAMPLES = [
    "station ke bahar ek amma leti hain, uth nahi paa rahi hain",
    "flyover ke neeche aadmi ke pair se khoon aa raha hai, patti gandi ho gayi hai",
    "teen bacche baarish mein bheeg rahe hain mandir ke peeche",
  ];
  let voiceIdx = 0;
  document.getElementById("btn-voice").addEventListener("click", () => {
    const t = VOICE_SAMPLES[voiceIdx++ % VOICE_SAMPLES.length];
    sendInbound("voice", { text: t });
  });
  document.getElementById("btn-script").addEventListener("click", async () => {
    const cycle = ["auto", "en", "hinglish", "deva"];
    const cur = state ? state.script : "auto";
    const next = cycle[(cycle.indexOf(cur) + 1) % cycle.length];
    await fetch("/api/script", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ script: next }) });
    refresh();
  });
  document.getElementById("conv-select").addEventListener("change", (e) => {
    activeConv = e.target.value; renderPhone();
  });
  document.querySelectorAll(".scenarios button").forEach((b) =>
    b.addEventListener("click", async () => {
      await fetch(`/api/scenario/${b.dataset.sc}`, { method: "POST" });
      if (b.dataset.sc === "golden_run") { followGolden = true; updateFollowBtn(); }
      refresh();
    }));
  document.getElementById("btn-follow").addEventListener("click", () => {
    followGolden = !followGolden;
    updateFollowBtn();
  });
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
  document.getElementById("resp-select").addEventListener("change", (e) => { selectedResp = e.target.value; renderRespPanel(); });
  document.getElementById("resp-manual").addEventListener("change", async (e) => {
    await fetch("/api/manual", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ responder_id: selectedResp, manual: e.target.checked }) });
    refresh();
  });
  document.getElementById("btn-sound").addEventListener("click", () => {
    soundOn = !soundOn;
    if (soundOn && !audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (soundOn) { beep(660, 0.07); beep(880, 0.07, 0.09); }
    document.getElementById("btn-sound").innerHTML = soundOn ? ICON_BELL : ICON_BELL_OFF;
  });
  document.getElementById("btn-export").addEventListener("click", async () => {
    const res = await fetch("/api/export");
    const blob = new Blob([JSON.stringify(await res.json(), null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "pukaar-session.json";
    a.click();
    URL.revokeObjectURL(a.href);
  });
}

function sendText() {
  const input = document.getElementById("msg-in");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  sendInbound("text", { text });
}

// ----------------------------------------------------------------- loop --
let pollFails = 0;
function connBanner(show) {
  let b = document.getElementById("conn-banner");
  if (!b && show) {
    b = document.createElement("div");
    b.id = "conn-banner";
    b.textContent = "⚠ connection lost — retrying…";
    document.body.appendChild(b);
  }
  if (b) b.hidden = !show;
}

async function refresh() {
  try {
    const res = await fetch("/api/state");
    state = await res.json();
    pollFails = 0;
    connBanner(false);
  } catch {
    if (++pollFails >= 2) connBanner(true);
    return;
  }
  if (!wired) { wire(); wired = true; }
  if (!map) {
    try { initMap(state.zone); } catch (err) {
      // Leaflet missing or map failure must never take the panels down.
      document.getElementById("map").innerHTML =
        '<div style="display:grid;place-items:center;height:100%;color:#898781">map unavailable — data panels live</div>';
      map = "failed";
    }
  }
  document.getElementById("clock").textContent =
    `${state.sim.is_night ? "🌙 " : ""}${state.sim.clock} · ${state.sim.speed}×`;
  document.getElementById("btn-pause").textContent = state.sim.running ? "⏸" : "▶";
  const speedSel = document.getElementById("speed");
  if ([...speedSel.options].some((o) => +o.value === state.sim.speed)) speedSel.value = String(state.sim.speed);
  document.getElementById("btn-script").textContent =
    { auto: "🌐", en: "EN", hinglish: "Hi", deva: "अ" }[state.script] || "🌐";
  document.getElementById("btn-script").title =
    `bot language: ${state.script}` + (state.script === "auto" ? " (mirrors the witness)" : "") + " — click to cycle";
  const badge = document.getElementById("backend-badge");
  badge.textContent = state.backend === "claude" ? "CLAUDE LIVE" : "MOCK AGENT";
  badge.classList.toggle("live", state.backend === "claude");
  document.getElementById("foot-backend").textContent = state.backend;
  document.getElementById("prov-note").textContent =
    state.prov_ephemeral ? "demo HMAC key (ephemeral) — set PUKAAR_HMAC_KEY for persistent provenance" : "persistent HMAC provenance key";
  syncMap(); renderTiles(); renderFeed(); renderCases(); renderPhone(); renderDetail();
  renderRespPanel(); renderCoord(); drawCells(); playNewFeedSounds();
  const veil = document.getElementById("boot-veil");
  if (veil && !veil.classList.contains("gone")) {
    veil.classList.add("gone");
    setTimeout(() => veil.remove(), 450);
  }
}

// ------------------------------------------------- 90-day cell heatmap --
// The privacy story, visible: after the purge, coarse cell + count is ALL
// the location data that still exists — so that's all this layer can show.
let cellsOn = false, cellRects = [], lastCellsKey = "";
function drawCells() {
  if (!map || map === "failed") return;
  if (!cellsOn) {
    if (cellRects.length) { cellRects.forEach((r) => r.remove()); cellRects = []; }
    lastCellsKey = "";
    return;
  }
  const cells = state.cells || [];
  const key = cells.map((c) => `${c.cell}/${c.category}/${c.n}`).join("|");
  if (key === lastCellsKey) return;
  lastCellsKey = key;
  cellRects.forEach((r) => r.remove());
  cellRects = [];
  const maxN = Math.max(1, ...cells.map((c) => c.n));
  for (const c of cells) {
    const color = CAT[c.category] || "#898781";
    const r = L.rectangle([[c.south, c.west], [c.north, c.east]], {
      color, weight: 1, opacity: 0.35, fillColor: color,
      fillOpacity: 0.12 + 0.38 * (c.n / maxN), interactive: true,
    }).addTo(map);
    r.bindTooltip(`${c.category} · ${c.n} case${c.n === 1 ? "" : "s"} — 90-day aggregate (all that survives the purge)`);
    cellRects.push(r);
  }
}

refresh();
setInterval(refresh, 1000);
