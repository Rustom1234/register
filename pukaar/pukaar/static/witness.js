/* Wayside witness app — the reporter's own view, standalone from the
   control room. Same backend the control room's phone panel drives
   (/api/wa/inbound, /api/state) — just scoped to one conversation, the
   way a real person's phone only ever sees their own thread. */
"use strict";

const $ = (id) => document.getElementById(id);

// Deep link: /witness?phone=+91-9xx-0001 opens that thread standalone;
// otherwise this browser keeps using the same demo number across visits.
// Validated before persisting: a crafted value (e.g. an object-prototype
// key) would otherwise brick the page AND stick via localStorage.
const PHONE_OK = /^[+0-9A-Za-z:_\-]{3,32}$/;
const urlPhone = new URLSearchParams(location.search).get("phone");
let activeConv = [urlPhone, localStorage.getItem("pukaar_witness_phone")]
  .find((p) => p && PHONE_OK.test(p)) || "+91-DEMO";
localStorage.setItem("pukaar_witness_phone", activeConv);

let state = null;
let map, witnessPin = null;
const localLog = [];
let typingUntil = 0;

// Offline shell: the same root service worker the rider app uses precaches
// this page — a witness with no signal sees the app (and an honest "didn't
// send"), not the browser's error page.
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => { /* http/old browser */ });
}

function netNote(msg, ok = false) {
  let n = $("net-note");
  if (!n) {
    n = document.createElement("div");
    n.id = "net-note";
    n.setAttribute("role", "status");
    n.style.cssText = "position:fixed;bottom:20px;left:50%;transform:translateX(-50%);" +
      "border-radius:999px;" +
      "padding:10px 18px;font-size:13px;font-weight:600;z-index:99;max-width:90vw;text-align:center";
    document.body.appendChild(n);
  }
  // colors per call, not per create: the one toast carries bad news and good —
  // ok swaps the red trio for its green twin (r/g channels mirrored)
  n.style.background = ok ? "#122a15" : "#2a1215";
  n.style.border = ok ? "1px solid #3bd03b" : "1px solid #d03b3b";
  n.style.color = ok ? "#9dff99" : "#ff9d99";
  n.textContent = msg;
  n.hidden = false;
  clearTimeout(netNote._t);
  netNote._t = setTimeout(() => { n.hidden = true; }, 4000);
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

// ------------------------------------------------------------------ map --
// Same Google-style local basemap the supervisor sees — day theme, since a
// witness is a member of the public, not an ops room.
function initMap(zone) {
  try {
    const dLat = (zone.radius_m * 2.6) / 111320;
    const dLng = dLat / Math.cos(zone.lat * Math.PI / 180);
    map = new maplibregl.Map({
      container: "map",
      style: WaysideBasemap.buildStyle("/data/demo_zone.geojson", "day", zone),
      center: [zone.lng, zone.lat],
      zoom: 14.9,
      minZoom: 13.2,
      maxZoom: 17.5,  // matches the data's detail ceiling (see app.js)
      maxBounds: [[zone.lng - dLng, zone.lat - dLat], [zone.lng + dLng, zone.lat + dLat]],
      attributionControl: { compact: true, customAttribution: "demo geometry — representative, not surveyed" },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.on("style.load", () => {
      // NB: "zone" is the basemap's street-data source — the ring is "zonering"
      if (map.getSource("zonering")) return;
      const pts = [];
      for (let i = 0; i <= 72; i++) {
        const a = (i / 72) * 2 * Math.PI;
        pts.push([
          zone.lng + (zone.radius_m * Math.sin(a)) / (111320 * Math.cos(zone.lat * Math.PI / 180)),
          zone.lat + (zone.radius_m * Math.cos(a)) / 111320,
        ]);
      }
      map.addSource("zonering", { type: "geojson",
        data: { type: "Feature", geometry: { type: "LineString", coordinates: pts } } });
      map.addLayer({ id: "zone-line", type: "line", source: "zonering",
        paint: { "line-color": "#6b6a66", "line-opacity": 0.7, "line-width": 1.2,
                 "line-dasharray": [2, 2.4] } });
    });
    // A double-tap to zoom fires two clicks first — placing the pin on a
    // short fuse and cancelling on dblclick keeps the universal phone
    // gesture from silently teleporting the dispatch location.
    let pinFuse = null;
    map.on("click", (e) => {
      clearTimeout(pinFuse);
      const { lat, lng } = e.lngLat;
      pinFuse = setTimeout(() => placeWitnessPin(lat, lng), 300);
    });
    map.on("dblclick", () => clearTimeout(pinFuse));
  } catch {
    $("map").innerHTML = '<div style="display:grid;place-items:center;height:100%;color:#898781">map unavailable — you can still type a landmark</div>';
    map = "failed";
  }
}

function placeWitnessPin(lat, lng) {
  if (map === "failed") return;
  if (!witnessPin) {
    const el = document.createElement("div");
    el.className = "witness-pin";
    el.textContent = "📍";
    witnessPin = new maplibregl.Marker({ element: el, draggable: true, anchor: "bottom" })
      .setLngLat([lng, lat]).addTo(map);
  } else witnessPin.setLngLat([lng, lat]);
}

// ---------------------------------------------------------------- phone --
function renderPhone() {
  $("conv-phone").textContent = activeConv;
  // own-property + shape check — never hand a prototype member to the
  // renderer no matter what the conversation key is
  const ownConv = state && Object.prototype.hasOwnProperty.call(state.conversations, activeConv)
    ? state.conversations[activeConv] : null;
  const log = Array.isArray(ownConv) ? ownConv : localLog;
  const msgs = $("msgs");
  const atBottom = msgs.scrollHeight - msgs.scrollTop - msgs.clientHeight < 60;
  const bubbleTime = (ts) => {
    if (!ts) return "";
    const h = String(Math.floor((ts % 86400) / 3600)).padStart(2, "0");
    const mm = String(Math.floor((ts % 3600) / 60)).padStart(2, "0");
    return ` · ${h}:${mm}`;
  };
  const typing = typingUntil > Date.now();
  const pend = outbox.filter((e) => e.phone === activeConv);
  const threadKey = `${activeConv}:${log.length}:${log.length ? log[log.length - 1].ts : 0}:${typing}:${pend.length}`;
  if (msgs.dataset.key !== threadKey) {
    const sameConv = msgs.dataset.conv === activeConv;
    const prevCount = sameConv ? +(msgs.dataset.count || 0) : Infinity;
    const greeting = log.length === 0 && !typing
      ? `<div class="bubble bot"><b>Hello 🙏 This is Wayside</b> — report someone on the street who needs help. Pick a scenario or type to begin.<span class="b-meta">Wayside</span></div>`
      : "";
    msgs.innerHTML = greeting + log.map((m, i) => {
      const who = m.from === "bot" ? "bot" : "witness";
      const fresh = i >= prevCount ? " fresh" : "";
      const voice = m.kind === "voice" ? ` voice" data-len="${3 + (m.text || "").length % 7}` : "";
      const hi = /[\u0900-\u097F]/.test(m.text || "") ? ' lang="hi"' : "";
      return `<div class="bubble ${who}${fresh}${voice}"${hi}>${escapeHtml(m.text)}<span class="b-meta">${who === "bot" ? "Wayside" : "you"}${bubbleTime(m.ts)}</span></div>`;
    }).join("") + pendingHtml() + (typing ? '<div class="bubble bot typing"><span></span><span></span><span></span></div>' : "");
    msgs.dataset.key = threadKey;
    msgs.dataset.conv = activeConv;
    msgs.dataset.count = String(log.length);
    if (atBottom) msgs.scrollTop = msgs.scrollHeight;
  }
  const last = log.length ? log[log.length - 1] : null;
  const quick = $("quick");
  const hasBtns = !!(last && last.from === "bot" && last.buttons && last.buttons.length);
  // keyed + escaped, same as the control room's quick row
  const quickKey = hasBtns ? `${last.ts}:${last.buttons.map((b) => b.id).join(",")}` : "";
  if (quick.dataset.key !== quickKey) {
    quick.dataset.key = quickKey;
    quick.innerHTML = hasBtns ? last.buttons.map((b) =>
      `<button data-payload="${escapeHtml(b.id)}">${escapeHtml(b.label)}</button>`).join("") : "";
    quick.querySelectorAll("button").forEach((btn) =>
      btn.addEventListener("click", () => sendInbound("button", { text: btn.dataset.payload })));
  }
}

function pendingHtml() {
  // Saved-but-unsent reports, drawn as the witness's own bubbles with an
  // honest clock — they flush (and vanish from here) when signal returns.
  return outbox.filter((e) => e.phone === activeConv).map((e) => {
    const txt = e.kind === "voice" ? "🎤 " + (e.extra.text || "")
      : e.kind === "photo" ? "📷 photo" : (e.extra.text || "");
    const hi = /[\u0900-\u097F]/.test(txt) ? ' lang="hi"' : "";
    return `<div class="bubble witness pending"${hi}>${escapeHtml(txt)}<span class="b-meta">🕓 saved — will send</span></div>`;
  }).join("");
}

// --------------------------------------------------------------- outbox --
// No-signal sends queue here and auto-flush on reconnect: a witness who
// walks off believing the report went through must not be silently wrong.
const OUTBOX_KEY = "pukaar_witness_outbox";
const OUTBOX_MAX = 10;
// never "button" — a button reply answers a bot prompt that may have moved on
const OUTBOX_KINDS = ["text", "location", "photo", "voice"];

// restore defensively: localStorage is user-writable, so validate the shape
// and drop malformed entries rather than letting one bad value brick sends
let outbox = (() => {
  try {
    const raw = JSON.parse(localStorage.getItem(OUTBOX_KEY) || "[]");
    return (Array.isArray(raw) ? raw : []).filter((e) =>
      e && OUTBOX_KINDS.includes(e.kind) && e.extra && typeof e.extra === "object"
    ).slice(-OUTBOX_MAX);
  } catch { return []; }
})();

function saveOutbox() {
  try { localStorage.setItem(OUTBOX_KEY, JSON.stringify(outbox)); } catch { /* private mode/quota */ }
}

// One id per LOGICAL message, minted when the witness hits send and reused
// on every retry — the server drops duplicates, so a send whose response
// got lost can't double-file the report.
function newCid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

function queueOutbound(kind, extra, cid) {
  if (!OUTBOX_KINDS.includes(kind)) return false;
  // phone captured NOW: a deep link can switch activeConv before the flush
  // runs, and a deferred report must land in the thread it was written in
  outbox.push({ kind, extra, ts: Date.now(), phone: activeConv, cid });
  while (outbox.length > OUTBOX_MAX) outbox.shift(); // cap: the oldest report is the stalest
  saveOutbox();
  return true;
}

let flushBusy = false; // "online" + poll recovery can fire together — one flush at a time
async function flushOutbox() {
  if (flushBusy || !outbox.length) return;
  flushBusy = true;
  let sent = 0;
  try {
    // strictly in order; a failure keeps the remainder (head included) for the
    // next trigger — never re-queued to the tail, which would reorder reports
    while (outbox.length) {
      const e = outbox[0];
      try {
        const res = await fetch("/api/wa/inbound", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ phone: e.phone || activeConv, kind: e.kind,
                                 client_id: e.cid, ...e.extra }),
        });
        await res.json();
      } catch { break; } // still (or again) offline
      outbox.shift(); // drop only after a confirmed send
      sent++;
    }
  } finally {
    saveOutbox();
    flushBusy = false;
  }
  if (sent) {
    netNote(`✓ ${sent} saved message${sent === 1 ? "" : "s"} sent.`, true);
    refresh();
  }
}

window.addEventListener("online", () => flushOutbox());

let sendBusy = false; // one in-flight report at a time — Enter-mash safe

async function sendInbound(kind, extra = {}) {
  if (kind === "text" || kind === "button") localEcho(extra.text, kind);
  else if (kind === "voice") localEcho("🎤 " + extra.text, "voice");
  // typing dots promise a reply — never show them with no signal
  if (navigator.onLine !== false) typingUntil = Date.now() + 900;
  renderPhone();
  // Order beats latency: while queued reports are waiting (or mid-flush), a
  // new queueable message joins the BACK of the line — sending it direct
  // would deliver it before older reports and garble the intake thread.
  if ((outbox.length || flushBusy) && OUTBOX_KINDS.includes(kind)) {
    queueOutbound(kind, extra, newCid());
    netNote("⚠ Queued behind your earlier saved messages — sending in order.");
    flushOutbox();
    setTimeout(() => { typingUntil = 0; refresh(); }, 700);
    return;
  }
  const cid = newCid();
  const body = { phone: activeConv, kind, client_id: cid, ...extra };
  const btn = $("btn-send");
  sendBusy = true;
  if (btn) btn.disabled = true;
  try {
    const res = await fetch("/api/wa/inbound", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    await res.json();
  } catch {
    // no signal: queue it — "try again" loses reports from witnesses who walk
    // away; button taps stay unqueued, so they keep the plain failure note.
    // Same cid: if the send actually landed and only the response was lost,
    // the server drops the redelivery instead of double-filing the report.
    if (queueOutbound(kind, extra, cid)) {
      netNote("⚠ No signal — saved. It will send by itself when you're back online.");
    } else {
      netNote("⚠ No signal — your message didn't send. Try again when you're connected.");
    }
  } finally {
    sendBusy = false;
    if (btn) btn.disabled = false;
    setTimeout(() => { typingUntil = 0; refresh(); }, 700);
  }
}

function localEcho(text, kind) {
  if (!state || !state.conversations[activeConv]) localLog.push({ from: "witness", kind, text, buttons: [] });
}

function sendText() {
  if (sendBusy) return; // the button is disabled, but Enter still fires
  const input = $("msg-in");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  sendInbound("text", { text });
}

// ---------------------------------------------------------------- wires --
function wire() {
  $("btn-send").addEventListener("click", sendText);
  $("msg-in").addEventListener("keydown", (e) => { if (e.key === "Enter") sendText(); });
  $("btn-loc").addEventListener("click", () => {
    // Only ever share a pin the witness actually placed. Inventing a
    // random nearby point here sent riders to a spot no human chose —
    // the one datum this product treats as sacred.
    if (!witnessPin) {
      netNote("📍 Tap the map where the person is first — then send the pin.");
      return;
    }
    const { lat, lng } = witnessPin.getLngLat();
    sendInbound("location", { lat, lng });
  });
  const photoMenu = $("photo-menu");
  $("btn-photo").addEventListener("click", () => { photoMenu.hidden = !photoMenu.hidden; });
  photoMenu.querySelectorAll("button[data-hint]").forEach((b) =>
    b.addEventListener("click", () => { photoMenu.hidden = true; sendInbound("photo", { photo_hint: b.dataset.hint }); }));
  // Real upload from the phone's gallery/camera. Files can't ride the
  // localStorage outbox, so offline gets an honest "connect first" note
  // instead of a fake queue.
  $("pm-upload").addEventListener("click", () => { $("pm-file").click(); });
  $("pm-file").addEventListener("change", async () => {
    const f = $("pm-file").files[0];
    photoMenu.hidden = true;
    if (!f) return;
    if (!navigator.onLine) {
      netNote("⚠ No signal — photos need a connection. Describe what you see in the chat instead.");
      $("pm-file").value = "";
      return;
    }
    if (f.size > 3 * 1024 * 1024) {
      netNote("⚠ That photo is over 3 MB — most phones can pick a smaller size.");
      $("pm-file").value = "";
      return;
    }
    localEcho("📷 photo (uploading…)", "photo");
    typingUntil = Date.now() + 1500;
    renderPhone();
    const fd = new FormData();
    fd.append("phone", activeConv);
    fd.append("client_id", Date.now().toString(36) + Math.random().toString(36).slice(2, 8));
    fd.append("file", f);
    try {
      const res = await fetch("/api/wa/photo", { method: "POST", body: fd });
      if (!res.ok) {
        const detail = (await res.json().catch(() => ({}))).detail || "upload failed";
        netNote(`⚠ ${detail}`);
      }
    } catch {
      netNote("⚠ No signal — the photo didn't send. Try again when you're connected.");
    } finally {
      $("pm-file").value = "";
      setTimeout(() => { typingUntil = 0; refresh(); }, 700);
    }
  });
  const VOICE_SAMPLES = [
    "station ke bahar ek amma leti hain, uth nahi paa rahi hain",
    "flyover ke neeche aadmi ke pair se khoon aa raha hai, patti gandi ho gayi hai",
    "teen bacche baarish mein bheeg rahe hain mandir ke peeche",
  ];
  let voiceIdx = 0;
  $("btn-voice").addEventListener("click", () => sendInbound("voice", { text: VOICE_SAMPLES[voiceIdx++ % VOICE_SAMPLES.length] }));
  document.querySelectorAll(".scenarios button").forEach((b) =>
    b.addEventListener("click", async () => {
      let res;
      try {
        res = await (await fetch(`/api/scenario/${b.dataset.sc}`, { method: "POST" })).json();
      } catch {
        netNote("⚠ No signal — scenarios need a connection.");
        return;
      }
      // Jump this view to the scenario's thread — a demo button that plays
      // its story in a conversation you can't see is a dead end.
      if (res.phone) activeConv = res.phone;
      refresh();
    }));
}

// ----------------------------------------------------------------- loop --
let wired = false, pollFails = 0;
function connBanner(show) {
  let b = $("conn-banner");
  if (!b && show) {
    b = document.createElement("div"); b.id = "conn-banner";
    b.textContent = "⚠ connection lost — retrying…";
    document.body.appendChild(b);
  }
  if (b) b.hidden = !show;
}

function liftVeil() {
  const veil = $("boot-veil");
  if (veil && !veil.classList.contains("gone")) {
    veil.classList.add("gone");
    setTimeout(() => veil.remove(), 450);
  }
}

async function refresh() {
  try {
    // scoped, public endpoint: just this witness's own thread + the zone —
    // works on a staff-token deploy where /api/state is (correctly) gated
    const res = await fetch("/api/witness/state?phone=" + encodeURIComponent(activeConv));
    state = await res.json();
    const backOnline = pollFails > 0; // poll just recovered from a dead spell
    pollFails = 0;
    connBanner(false);
    if (backOnline) flushOutbox();
  } catch {
    // Offline boot (service-worker shell): the page must still be USABLE —
    // a veil that waits for a poll that can never succeed is a dead app.
    // Lift it, wire the inputs, init the map from the cached zone (the SW
    // precached MapLibre + street data for exactly this), and let the send
    // path say "no signal".
    if (!wired) {
      wire(); wired = true;
      if (!map) {
        try {
          const z = JSON.parse(localStorage.getItem("pukaar_witness_zone") || "null");
          if (z && z.lat != null) initMap(z);
        } catch { /* no cached zone yet — map stays blank, chat still works */ }
      }
      renderPhone(); liftVeil();
    }
    if (++pollFails >= 2) connBanner(true);
    return;
  }
  if (!wired) { wire(); wired = true; }
  if (!map) {
    initMap(state.zone);
    // remember the zone so an offline BOOT can still draw the street map
    try { localStorage.setItem("pukaar_witness_zone", JSON.stringify(state.zone)); } catch { /* quota */ }
  }
  renderPhone();
  liftVeil();
}

// boot: reports queued on an earlier no-signal visit go out straight away
if (outbox.length && navigator.onLine) flushOutbox();
refresh();
setInterval(refresh, 1000);
