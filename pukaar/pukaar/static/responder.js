/* Wayside responder app — the field worker's side of the marketplace.
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
function fmtDur(s) {
  if (s == null) return "—";
  return s < 90 ? `${Math.round(s)} s` : `${Math.round(s / 60)} min`;
}

let state = null;
let myId = localStorage.getItem("pukaar_resp") || "";
// Deep link: /responder?id=resp_3 picks the identity AND goes on duty —
// hand a phone a URL and it's a responder, no taps needed.
const urlId = new URLSearchParams(location.search).get("id");
if (urlId) {
  myId = urlId;
  localStorage.setItem("pukaar_resp", myId);
}
let autoDuty = !!urlId;
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
// Deep-linked riders (?id=...) went on duty without a click; a tap is the
// user gesture that lets us ask for notification permission. NOT {once}:
// the first tap usually lands before the first /api/state poll resolves
// (me() still null), and a one-shot would burn the only chance — stay
// armed until the ask actually happened for an on-duty identity.
function armNotifyTap() {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    audioCtx.resume();
  } catch { /* ignore */ }
  const m = me();
  if (m && m.manual) {
    enableNotifications();
    document.removeEventListener("pointerdown", armNotifyTap);
  }
}
document.addEventListener("pointerdown", armNotifyTap);

async function api(path, body) {
  // Never throws: the offline shell means every button here can be tapped
  // with zero signal, and an unhandled rejection = a silently eaten tap.
  try {
    const r = await fetch(path, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    // AWAIT: a non-JSON response (500 HTML, proxy error page) makes r.json()
    // reject — unawaited, that rejection escapes the try and leaves the
    // tapped button dead forever. Awaited, it degrades to the offline path.
    return await r.json();
  } catch {
    return { ok: false, offline: true };
  }
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

function me() {
  return state ? state.sim.responders.find((r) => r.id === myId) || null : null;
}

function show(id) {
  for (const s of ["scr-pick", "scr-idle", "scr-offers", "scr-active"]) {
    $(s).hidden = s !== id;
  }
  // The single-card off-duty pick screen centers in the tall phone; the
  // idle screen now carries a live activity feed, so it top-aligns like the
  // list/active screens.
  document.querySelector("main").classList.toggle("centered", id === "scr-pick");
}

function toast(txt) {
  const t = $("toast");
  t.textContent = txt;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 1600);
}

/* ------------------------------------------------------------ screens -- */

function renderPick() {
  // Offline shell boot: an empty select renders as a broken white box —
  // say why it's empty instead.
  if (!pickFilled && !$("pick").options.length) {
    $("pick").innerHTML = '<option value="" disabled selected>no signal — connect once to load names</option>';
  }
  if (!pickFilled && state.sim.responders.length) {
    $("pick").innerHTML = state.sim.responders
      .map((r) => `<option value="${escapeHtml(r.id)}">${escapeHtml(r.name)}${r.medical ? " · medical-trained" : ""}</option>`)
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
  renderIdleFeed();
  show("scr-idle");
}

// A read-only mini-feed of the last few dispatch events — the poll already
// carries state.feed, so this reads as a live system with no new API.
const AF_ICON = {
  order_accepted: ["✅", "good"], responder_arrived: ["📍", ""],
  outcome: ["🟢", "good"], order_created: ["📦", ""], wave_started: ["📣", ""],
  case_created: ["🆕", ""], coordinator_alert: ["⚠️", "warn"], emergency_redirect: ["🚨", "crit"],
};
function renderIdleFeed() {
  const el = $("idle-feed");
  if (!el) return;
  const kept = (state.feed || []).filter((e) => AF_ICON[e.kind]).slice(-6).reverse();
  if (!kept.length) return;   // keep the "quiet" placeholder
  const t = (ts) => `${String(Math.floor((ts % 86400) / 3600)).padStart(2, "0")}:` +
                    `${String(Math.floor((ts % 3600) / 60)).padStart(2, "0")}`;
  const nm = (id) => escapeHtml((state.sim.responders.find((r) => r.id === id) || { name: "" }).name);
  const line = (e) => {
    switch (e.kind) {
      case "order_accepted": return `${nm(e.responder_id)} accepted a call`;
      case "responder_arrived": return `${nm(e.responder_id)} reached the spot`;
      case "outcome": return `case ${(e.case_id || "").slice(-4).toUpperCase()} · ${e.outcome}`;
      case "order_created": return `new ${e.sku} order · ${e.priority}`;
      case "wave_started": return `offers out for ${(e.order_id || "").slice(-4).toUpperCase()}`;
      case "case_created": return `new case · ${e.category || "?"}`;
      case "coordinator_alert": return `coordinator: ${e.reason}`;
      case "emergency_redirect": return `112 emergency redirect`;
      default: return e.kind;
    }
  };
  el.innerHTML = kept.map((e) => {
    const [ic, cls] = AF_ICON[e.kind];
    return `<li class="${cls}"><span class="af-t">${t(e.ts)}</span><span>${ic} ${line(e)}</span></li>`;
  }).join("");
}

function offerCard(a, order, c) {
  const m = me();
  const dist = c && c.lat != null && m
    ? `${Math.round(haversineM(m.lat, m.lng, c.lat, c.lng))} m` : "—";
  const ttl = (state.config && state.config.offer_ttl_s) || 180;
  const left = Math.max(0, a.offered_at + ttl - state.sim.sim_now);
  const kit = (state.kit_skus[order.sku] || {}).name || order.sku;
  const wallLeft = Math.max(1, Math.round(left / ((state.sim && state.sim.speed) || 1)));
  const leftTxt = wallLeft < 95 ? `${wallLeft} s left` : `${Math.ceil(wallLeft / 60)} min left`;
  return `<div class="card offer ${order.priority === "P1" ? "p1" : ""}" data-aid="${a.id}">
    <div class="row1">
      <span class="pill ${order.priority === "P1" ? "p1" : "p2"}">${order.priority}</span>
      <span class="kit">${CAT_ICON[c && c.category] || "•"} ${kit}</span>
    </div>
    <div class="meta"><span>📍 ${dist}</span><span>${c ? c.digipin || "" : ""}</span>
      <span>wave ${order.wave || 1}</span>${order.clinical_flag ? "<span>🩺 clinical flag</span>" : ""}</div>
    <div class="ttl" aria-label="time left to accept"><i style="width:${(left / ttl) * 100}%"></i></div>
    <div class="btnrow">
      <button class="big" data-acc="${a.id}">ACCEPT · <span lang="hi">लो</span><span class="hn">${leftTxt}</span></button>
      <button class="big decline" data-dec="${a.id}">Pass<span class="hn" lang="hi">छोड़ें</span></button>
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
      // only refresh the countdown sub-label — textContent would wipe the
      // Hindi span baked into the button
      const accHn = acc && acc.querySelector(".hn");
      if (acc && !acc.disabled && accHn) accHn.textContent = `${leftTxt}`;
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
      if (res.offline) {
        b.disabled = false;
        toast("⚠ no signal — try again");
        return;
      }
      toast(res.ok ? "✓ accepted — head to the pin" : "offer already taken");
    }));
  scr.querySelectorAll("[data-dec]").forEach((b) =>
    b.addEventListener("click", async () => {
      b.disabled = true;
      const res = await api("/api/responder", { action: "decline", assignment_id: b.dataset.dec });
      if (res.offline) { b.disabled = false; toast("⚠ no signal — try again"); }
      else toast("Passed — the offer moves on · अगले को जाएगा");
    }));
  show("scr-offers");
}

// Turn-by-turn text mode ("Ghalib Road · 240 m"): the sim serves the
// collapsed steps + current index, so this is pure presentation. Absent
// steps (legacy order, no road graph) render nothing — never a broken box.
function stepsHtml(steps, stepI) {
  if (!steps || !steps.length) return "";
  const fmtM = (v) => (v >= 1000 ? `${(v / 1000).toFixed(1)} km` : `${v} m`);
  // street names are data, not markup: today they come from our own
  // geojson, but tools/fetch_real_roads.py imports OSM names verbatim —
  // an innerHTML sink must never trust them
  return `<ol class="steps">` + steps.map((s, i) =>
    `<li class="${i < stepI ? "done" : i === stepI ? "now" : ""}">` +
    `<span class="st-n">${escapeHtml(s.street)}</span><span class="st-m">${fmtM(s.m)}</span></li>`).join("") + `</ol>`;
}

let activeKey = "";
function renderActive(order) {
  const m = me();
  const c = state.cases.find((x) => x.id === order.case_id);
  const kit = state.kit_skus[order.sku] || { name: order.sku, contents: "" };
  // Road-routed distance/ETA from the sim (not a beeline — matches what the
  // control room map is actually animating along).
  const dist = m && m.dist_m != null ? m.dist_m : null;
  const eta = m && m.eta_s != null ? m.eta_s : null;
  const steps = (m && m.steps) || null;
  const stepI = m && m.step_i != null ? m.step_i : -1;
  if (order.status === "accepted" && dist != null && !startDist.has(order.id)) {
    startDist.set(order.id, Math.max(dist, 1));
  }
  const pct = dist != null && startDist.has(order.id)
    ? Math.max(0, Math.min(100, 100 - (dist / startDist.get(order.id)) * 100)) : 0;
  const onsite = order.status === "onsite";
  const pickupPending = m && m.depot && !m.picked_up && !onsite;
  // Steps land a tick after a human-tapped accept (the sim reconciles on
  // its next tick) — keying on their count rebuilds once they arrive.
  const key = `${order.id}:${order.status}:${pickupPending}:${steps ? steps.length : 0}`;
  if (key === activeKey && !$("scr-active").hidden) {
    // Same order & phase: move the distance readout, progress bar and step
    // highlight in place; never rebuild the DOM under the outcome buttons.
    if (!onsite) {
      const d = $("scr-active").querySelector(".dist");
      if (d) d.innerHTML = `${fmtDur(eta)}<small> away · ${dist != null ? Math.round(dist) : "—"} m by road</small>`;
      const bar = $("scr-active").querySelector(".bar i");
      if (bar) bar.style.width = `${pct}%`;
      $("scr-active").querySelectorAll(".steps li").forEach((li, i) => {
        li.classList.toggle("done", i < stepI);
        li.classList.toggle("now", i === stepI);
      });
    }
    return;
  }
  activeKey = key;
  offersKey = "";
  const checklist = kit.contents
    ? `<ul class="check">${kit.contents.split(", ").map((x) => `<li>${x}</li>`).join("")}</ul>` : "";
  // Unknown ids fall back to the raw string — which on the live backend is
  // model output, so it must be escaped like any other untrusted text.
  const instr = J(order.instruction_ids, [])
    .map((i) => `<li>${state.instructions[i] || escapeHtml(i)}</li>`).join("");
  $("scr-active").innerHTML = `
    <div class="banner ${onsite ? "onsite" : "enroute"}">${onsite ? 'AT THE PIN · <span lang="hi">पहुँच गए</span>' : 'EN ROUTE · <span lang="hi">रास्ते में</span>'}</div>
    <div class="card">
      <h2>Case ${order.case_id.slice(-4).toUpperCase()} · ${order.priority}</h2>
      <div class="digipin">${c ? c.digipin || "—" : "—"}</div>
      ${onsite
        ? `<p class="hint">You're on site. Give what's needed, then record what happened —
           the witness gets the closure message automatically.</p>`
        : `<div class="dist">${fmtDur(eta)}<small> away · ${dist != null ? Math.round(dist) : "—"} m by road</small></div>
           <div class="bar"><i style="width:${pct}%"></i></div>
           ${stepsHtml(steps, stepI)}
           ${pickupPending
             ? `<p class="hint">📦 <b>Collect the kit at ${m.depot}</b> · <span class="hn" lang="hi">पहले ${m.depot} से किट लें</span> — it's on your route, the detour is already in your ETA.</p>`
             : (m && m.depot ? `<p class="hint">✅ Kit collected at ${m.depot} · <span class="hn" lang="hi">किट मिल गई</span></p>` : "")}
           <p class="hint">Arrival registers automatically at the pin — or tap below
           when you're there.</p>
           <button class="big arrived" data-arrived="${order.id}">📍 I've arrived<span class="hn" lang="hi">पहुँच गया</span></button>`}
    </div>
    <div class="card">
      <h2>${CAT_ICON[c && c.category] || ""} ${kit.name} (${order.sku})</h2>
      ${checklist}
      ${order.clinical_flag ? '<p class="hint">🩺 clinical flag — medical escalation pre-approved.</p>' : ""}
    </div>
    ${instr ? `<div class="card"><h2>On arrival</h2><ol class="instr">${instr}</ol></div>` : ""}
    ${onsite ? `
    <div class="outgrid">
      <button class="big served" data-out="served">🟢 Help given<span class="hn" lang="hi">मदद दे दी</span></button>
      <button class="big escal" data-out="escalated">🩺 Call medical<span class="hn" lang="hi">डॉक्टर बुलाओ</span></button>
      <button class="big plain" data-out="not_found">Not found<span class="hn" lang="hi">नहीं मिला</span></button>
      <button class="big plain" data-out="declined">Declined help<span class="hn" lang="hi">मना किया</span></button>
    </div>` : ""}`;
  $("scr-active").querySelectorAll("[data-out]").forEach((b) =>
    b.addEventListener("click", async () => {
      b.disabled = true;
      const res = await api("/api/responder",
        { action: "outcome", order_id: order.id, outcome: b.dataset.out });
      if (res.offline) {
        b.disabled = false;
        toast("⚠ no signal — outcome not recorded, try again");
        return;
      }
      if (res.ok) { toast("✓ outcome recorded"); startDist.delete(order.id); }
    }));
  const arr = $("scr-active").querySelector("[data-arrived]");
  if (arr) arr.addEventListener("click", async () => {
    // success is claimed only AFTER the server says so — a false "✓" to a
    // rider standing at the pin with no signal is worse than no button
    arr.disabled = true;
    const res = await api("/api/responder", { action: "arrived", order_id: order.id });
    if (res.offline) {
      arr.disabled = false;
      toast("⚠ no signal — arrival auto-registers at the pin anyway");
      return;
    }
    arr.textContent = "✓ marked arrived";
    if (res.ok) { toast("✓ arrived"); activeKey = ""; }
  });
  show("scr-active");
}

/* --------------------------------------------------------------- main -- */

function render() {
  if (!state) return;
  $("clock").textContent = state.sim.clock;
  const m = me();
  const onDuty = !!(m && m.manual);
  // innerHTML (not textContent) so the Hindi carries lang="hi" for screen
  // readers; the responder name is escaped since it's the only variable part
  $("duty-pill").innerHTML = onDuty
    ? `on duty · <span lang="hi">ड्यूटी पर</span> · ${escapeHtml(m.name)}`
    : `off duty · <span lang="hi">ड्यूटी बंद</span>`;
  $("duty-pill").classList.toggle("on", onDuty);
  $("sos-btn").hidden = !onDuty;
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
  for (const { a, order, c } of offers) {
    if (!seenOffers.has(a.id)) {
      seenOffers.add(a.id);
      beep(988); beep(784);
      localNotify("Wayside — new offer",
        `${order.sku}${c && c.category ? " · " + c.category : ""} · first accept wins`);
    }
  }
  if (offers.length) { renderOffers(offers); return; }
  renderIdle(m);
}

let pollBusy = false;
async function poll() {
  // overlap guard + timeout: on a slow phone network stacked polls resolve
  // out of order and flap the offer/step UI backward for a frame
  if (pollBusy) return;
  pollBusy = true;
  const ctrl = new AbortController();
  const tid = setTimeout(() => ctrl.abort(), 4000);
  try {
    state = await (await fetch("/api/state", { signal: ctrl.signal })).json();
    $("f-status").textContent = "live";
    if (autoDuty) {
      autoDuty = false;
      const m = me();
      if (m && !m.manual) {
        await api("/api/manual", { responder_id: myId, manual: true });
        state = await (await fetch("/api/state")).json();
      }
    }
    render();
  } catch {
    $("f-status").textContent = "reconnecting…";
  } finally {
    clearTimeout(tid);
    pollBusy = false;
  }
}

$("duty-btn").addEventListener("click", async () => {
  // offline shell boot: #pick has no options yet — going "on duty" as ""
  // would clobber the saved identity in localStorage and then fail anyway
  if (!$("pick").value) {
    toast("⚠ no signal — identities load when you're connected");
    return;
  }
  myId = $("pick").value;
  localStorage.setItem("pukaar_resp", myId);
  const res = await api("/api/manual", { responder_id: myId, manual: true });
  if (res.offline) { toast("⚠ no signal — try again when connected"); return; }
  enableNotifications();     // needs the user gesture we just got
  await poll();
});

$("duty-off").addEventListener("click", async () => {
  await api("/api/manual", { responder_id: myId, manual: false });
  await poll();
});

// ------------------------------------------------ app-ness & notifying --
// Installable app: register the service worker (harmless if unsupported).
let swReg = null;
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js")
    .then((r) => { swReg = r; })
    .catch(() => { /* http or old browser — the page still works */ });
}

// Real push (phone buzzes with the app closed) when the server has keys
// and the browser supports it; in-page notifications otherwise.
async function enableNotifications() {
  try {
    if (!("Notification" in window)) return;
    if (Notification.permission === "default") await Notification.requestPermission();
    if (Notification.permission !== "granted") return;
    const { key } = await (await fetch("/api/push/vapid")).json();
    if (!key || !swReg || !("pushManager" in swReg)) return;
    const b64 = (key + "=".repeat((4 - key.length % 4) % 4)).replace(/-/g, "+").replace(/_/g, "/");
    const raw = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    // A fresh server DB mints a fresh VAPID keypair; subscribing over an
    // old-key subscription throws InvalidStateError forever. Reconcile:
    // drop a stale subscription first (same-key resubscribe is a no-op).
    const cur = await swReg.pushManager.getSubscription();
    if (cur) {
      const k = new Uint8Array(cur.options.applicationServerKey || []);
      if (k.length !== raw.length || k.some((b, i) => b !== raw[i])) await cur.unsubscribe();
    }
    const sub = await swReg.pushManager.subscribe({
      userVisibleOnly: true, applicationServerKey: raw });
    await api("/api/push/subscribe", { responder_id: myId, subscription: sub.toJSON() });
  } catch { /* denied / unsupported / offline push service — beeps still work */ }
}

// In-page fallback: a system notification for offers that arrive while the
// tab is hidden (covers the no-push cases: iOS un-installed, http, sandbox).
function localNotify(title, body) {
  try {
    if (document.visibilityState === "visible") return;
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    if (swReg && swReg.showNotification) {
      swReg.showNotification(title, { body, icon: "/static/icons/icon-192.png", tag: "wayside-offer" });
    } else {
      new Notification(title, { body, icon: "/static/icons/icon-192.png" });
    }
  } catch { /* notifications are best-effort */ }
}

// SOS: one tap, coordinator alerted, loudly.
$("sos-btn").addEventListener("click", async () => {
  if (!myId) return;
  const res = await api("/api/responder", { action: "sos", responder_id: myId });
  if (res.ok) toast("🆘 coordinator alerted");
});

poll();
setInterval(poll, 1000);
