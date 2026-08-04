/* Wayside session replay — animates an exported session JSON on a map+feed.
   Made for screen recording: scrub anywhere, play at 30-300x sim speed. */
"use strict";

const CAT = { medical: "#3987e5", food: "#d95926", shelter: "#199e70" };
let data = null, map = null, markers = new Map(), t0 = 0, t1 = 1, tNow = 0;
let playing = false, timer = null, cellRects = [];

function fmtT(ts) {
  const d = Math.floor(ts / 86400), h = String(Math.floor((ts % 86400) / 3600)).padStart(2, "0");
  const m = String(Math.floor((ts % 3600) / 60)).padStart(2, "0");
  return `Day ${d} · ${h}:${m}`;
}

function feedText(e) {
  const s = (id) => (id || "").slice(-4).toUpperCase();
  switch (e.kind) {
    case "case_created": return `🆕 case ${s(e.case_id)} · ${e.category || "?"}`;
    case "case_merged": return `👥 witness #${e.witnesses} merged into ${s(e.case_id)}`;
    case "order_created": return `📦 ${e.sku} · ${e.priority}${e.clinical_flag ? " · 🩺" : ""}`;
    case "wave_started": return `📣 ${s(e.order_id)} wave ${e.wave}`;
    case "order_accepted": return `✅ accepted ${s(e.order_id)} (wave ${e.wave})`;
    case "responder_arrived": return `📍 responder on site`;
    case "outcome": return `● ${s(e.case_id)} ${e.outcome}`;
    case "escalation_complete": return `🩺 escalation completed ${s(e.case_id)}`;
    case "emergency_redirect": return `🚨 112 redirect (no agent)`;
    case "coordinator_alert": return `⚠️ coordinator: ${e.reason}`;
    case "night_hold": return `🌙 ${s(e.case_id)} held for morning`;
    case "manual_assign": return `🧑‍✈️ manual assign ${s(e.order_id)}`;
    case "purge": return `🧹 purge m${e.media}/g${e.latlng}/r${e.cases}/o${e.orphan_reports ?? 0}`;
    default: return e.kind;
  }
}

function load(json) {
  data = json;
  data.feed.sort((a, b) => a.ts - b.ts);
  t0 = data.feed.length ? data.feed[0].ts : 0;
  t1 = data.feed.length ? data.feed[data.feed.length - 1].ts + 60 : t0 + 1;
  tNow = t0;
  document.getElementById("drop")?.remove();
  if (!map) {
    const first = data.cases.find((c) => c.lat != null);
    map = L.map("rmap", { zoomControl: false }).setView(
      first ? [first.lat, first.lng] : [28.5933, 77.2507], 15);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      { maxZoom: 19, attribution: "&copy; OSM &copy; CARTO" }).addTo(map);
  }
  // static underlay: the 90-day aggregate cells captured in the export
  cellRects.forEach((r) => r.remove());
  cellRects = [];
  for (const c of data.cells || []) {
    if (c.south == null) continue;
    const color = CAT[c.category] || "#898781";
    cellRects.push(L.rectangle([[c.south, c.west], [c.north, c.east]], {
      color, weight: 1, opacity: 0.22, fillColor: color, fillOpacity: 0.09,
    }).addTo(map).bindTooltip(`${c.category} · ${c.n} — 90-day aggregate`));
  }
  render();
}

function caseStateAt(c, ts) {
  // derive appearance from feed events up to ts
  const created = data.feed.find((e) => e.kind === "case_created" && e.case_id === c.id);
  if (!created || created.ts > ts) return null;
  const done = data.feed.find((e) => e.kind === "outcome" && e.case_id === c.id && e.ts <= ts);
  return done ? "closed" : "open";
}

function render() {
  document.getElementById("rclock").textContent = fmtT(tNow);
  document.getElementById("scrub").value = Math.round(1000 * (tNow - t0) / (t1 - t0));
  // feed (newest at bottom via column-reverse)
  const feedEl = document.getElementById("rfeed");
  const upto = data.feed.filter((e) => e.ts <= tNow).slice(-80).reverse();
  feedEl.innerHTML = upto.map((e) =>
    `<div class="fi"><span class="t">${fmtT(e.ts).split("· ")[1]}</span><span>${feedText(e)}</span></div>`).join("");
  // markers
  if (map) {
    for (const c of data.cases) {
      if (c.lat == null) continue;
      const st = caseStateAt(c, tNow);
      const key = c.id;
      if (!st) {
        if (markers.has(key)) { markers.get(key).remove(); markers.delete(key); }
        continue;
      }
      const color = CAT[c.category] || "#898781";
      const html = `<div class="case-pin${st === "closed" ? " closedc" : ""}" style="background:${color};position:relative"></div>`;
      if (!markers.has(key)) {
        markers.set(key, L.marker([c.lat, c.lng],
          { icon: L.divIcon({ className: "", html, iconSize: [16, 16], iconAnchor: [8, 8] }) }).addTo(map));
      } else {
        markers.get(key).setIcon(L.divIcon({ className: "", html, iconSize: [16, 16], iconAnchor: [8, 8] }));
      }
    }
  }
}

function tick() {
  if (!playing || !data) return;
  const speed = +document.getElementById("rspeed").value;
  tNow = Math.min(t1, tNow + speed / 5);       // called 5x per second
  render();
  if (tNow >= t1) setPlaying(false);
}

function setPlaying(on) {
  playing = on;
  document.getElementById("rplay").textContent = on ? "⏸" : "▶";
  if (on && !timer) timer = setInterval(tick, 200);
  if (!on && timer) { clearInterval(timer); timer = null; }
}

document.getElementById("rplay").addEventListener("click", () => setPlaying(!playing));
document.getElementById("rspeed").addEventListener("change", () => {});
document.getElementById("scrub").addEventListener("input", (e) => {
  if (!data) return;
  tNow = t0 + (t1 - t0) * (+e.target.value / 1000);
  render();
});
document.getElementById("rload").addEventListener("click", async () => {
  const r = await fetch("/api/export");
  load(await r.json());
});
document.getElementById("rfile").addEventListener("change", async (e) => {
  const f = e.target.files[0];
  if (f) load(JSON.parse(await f.text()));
});
