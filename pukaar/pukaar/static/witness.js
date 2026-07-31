/* Pukaar witness app — the reporter's own view, standalone from the
   control room. Same backend the control room's phone panel drives
   (/api/wa/inbound, /api/state) — just scoped to one conversation, the
   way a real person's phone only ever sees their own thread. */
"use strict";

const $ = (id) => document.getElementById(id);

// Deep link: /witness?phone=+91-9xx-0001 opens that thread standalone;
// otherwise this browser keeps using the same demo number across visits.
const urlPhone = new URLSearchParams(location.search).get("phone");
let activeConv = urlPhone || localStorage.getItem("pukaar_witness_phone") || "+91-DEMO";
localStorage.setItem("pukaar_witness_phone", activeConv);

let state = null;
let map, witnessPin = null;
const localLog = [];
let typingUntil = 0;

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

// ------------------------------------------------------------------ map --
function initMap(zone) {
  try {
    map = L.map("map", { zoomControl: true }).setView([zone.lat, zone.lng], 15);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    }).addTo(map);
    L.circle([zone.lat, zone.lng], {
      radius: zone.radius_m, color: "#898781", weight: 1.2, dashArray: "6 7", fill: false, opacity: 0.7,
    }).addTo(map);
    map.on("click", (e) => placeWitnessPin(e.latlng.lat, e.latlng.lng));
  } catch {
    $("map").innerHTML = '<div style="display:grid;place-items:center;height:100%;color:#898781">map unavailable — you can still type a landmark</div>';
    map = "failed";
  }
}

function placeWitnessPin(lat, lng) {
  if (map === "failed") return;
  if (!witnessPin) {
    witnessPin = L.marker([lat, lng], {
      draggable: true,
      icon: L.divIcon({ className: "", html: '<div class="witness-pin">📍</div>', iconAnchor: [11, 22] }),
    }).addTo(map);
  } else witnessPin.setLatLng([lat, lng]);
}

// ---------------------------------------------------------------- phone --
function renderPhone() {
  $("conv-phone").textContent = activeConv;
  const log = (state && state.conversations[activeConv]) || localLog;
  const msgs = $("msgs");
  const atBottom = msgs.scrollHeight - msgs.scrollTop - msgs.clientHeight < 60;
  const bubbleTime = (ts) => {
    if (!ts) return "";
    const h = String(Math.floor((ts % 86400) / 3600)).padStart(2, "0");
    const mm = String(Math.floor((ts % 3600) / 60)).padStart(2, "0");
    return ` · ${h}:${mm}`;
  };
  const typing = typingUntil > Date.now();
  const threadKey = `${activeConv}:${log.length}:${log.length ? log[log.length - 1].ts : 0}:${typing}`;
  if (msgs.dataset.key !== threadKey) {
    const sameConv = msgs.dataset.conv === activeConv;
    const prevCount = sameConv ? +(msgs.dataset.count || 0) : Infinity;
    const greeting = log.length === 0 && !typing
      ? `<div class="bubble bot"><b>Hello 🙏 This is Pukaar</b> — report someone on the street who needs help. Pick a scenario or type to begin.<span class="b-meta">Pukaar</span></div>`
      : "";
    msgs.innerHTML = greeting + log.map((m, i) => {
      const who = m.from === "bot" ? "bot" : "witness";
      const fresh = i >= prevCount ? " fresh" : "";
      const voice = m.kind === "voice" ? ` voice" data-len="${3 + (m.text || "").length % 7}` : "";
      return `<div class="bubble ${who}${fresh}${voice}">${escapeHtml(m.text)}<span class="b-meta">${who === "bot" ? "Pukaar" : "you"}${bubbleTime(m.ts)}</span></div>`;
    }).join("") + (typing ? '<div class="bubble bot typing"><span></span><span></span><span></span></div>' : "");
    msgs.dataset.key = threadKey;
    msgs.dataset.conv = activeConv;
    msgs.dataset.count = String(log.length);
    if (atBottom) msgs.scrollTop = msgs.scrollHeight;
  }
  const last = log.length ? log[log.length - 1] : null;
  const quick = $("quick");
  if (last && last.from === "bot" && last.buttons && last.buttons.length) {
    quick.innerHTML = last.buttons.map((b) => `<button data-payload="${b.id}">${b.label}</button>`).join("");
    quick.querySelectorAll("button").forEach((btn) =>
      btn.addEventListener("click", () => sendInbound("button", { text: btn.dataset.payload })));
  } else quick.innerHTML = "";
}

async function sendInbound(kind, extra = {}) {
  const body = { phone: activeConv, kind, ...extra };
  if (kind === "text" || kind === "button") localEcho(extra.text, kind);
  else if (kind === "voice") localEcho("🎤 " + extra.text, "voice");
  typingUntil = Date.now() + 900;
  renderPhone();
  const res = await fetch("/api/wa/inbound", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  await res.json();
  setTimeout(() => { typingUntil = 0; refresh(); }, 700);
}

function localEcho(text, kind) {
  if (!state || !state.conversations[activeConv]) localLog.push({ from: "witness", kind, text, buttons: [] });
}

function sendText() {
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
    let lat, lng;
    if (witnessPin) ({ lat, lng } = witnessPin.getLatLng());
    else if (state) {
      const z = state.zone;
      lat = z.lat + (Math.random() - 0.5) * 0.012; lng = z.lng + (Math.random() - 0.5) * 0.012;
      if (map && map !== "failed") placeWitnessPin(lat, lng);
    } else return;
    sendInbound("location", { lat, lng });
  });
  const photoMenu = $("photo-menu");
  $("btn-photo").addEventListener("click", () => { photoMenu.hidden = !photoMenu.hidden; });
  photoMenu.querySelectorAll("button[data-hint]").forEach((b) =>
    b.addEventListener("click", () => { photoMenu.hidden = true; sendInbound("photo", { photo_hint: b.dataset.hint }); }));
  const VOICE_SAMPLES = [
    "station ke bahar ek amma leti hain, uth nahi paa rahi hain",
    "flyover ke neeche aadmi ke pair se khoon aa raha hai, patti gandi ho gayi hai",
    "teen bacche baarish mein bheeg rahe hain mandir ke peeche",
  ];
  let voiceIdx = 0;
  $("btn-voice").addEventListener("click", () => sendInbound("voice", { text: VOICE_SAMPLES[voiceIdx++ % VOICE_SAMPLES.length] }));
  document.querySelectorAll(".scenarios button").forEach((b) =>
    b.addEventListener("click", async () => { await fetch(`/api/scenario/${b.dataset.sc}`, { method: "POST" }); refresh(); }));
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
  if (!map) initMap(state.zone);
  renderPhone();
  const veil = $("boot-veil");
  if (veil && !veil.classList.contains("gone")) {
    veil.classList.add("gone");
    setTimeout(() => veil.remove(), 450);
  }
}

refresh();
setInterval(refresh, 1000);
