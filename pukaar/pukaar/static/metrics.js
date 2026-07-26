/* Pukaar metrics page — hand-rolled SVG stacked bars per the dataviz method:
   thin marks, 2px surface gaps between segments, direct total labels,
   status colors reserved for outcomes (with icon+label legend), table view. */
"use strict";

const CATS = [["medical", "#3987e5"], ["food", "#d95926"], ["shelter", "#199e70"]];
const OUTS = [["served", "#0ca30c"], ["escalated", "#ec835a"], ["not_found", "#fab219"], ["declined", "#898781"]];
const SURFACE = "#12141a";

function stackedBars(svgId, rows, series, labelOf) {
  // rows: [{label, values: {seriesKey: n}}]
  const svg = document.getElementById(svgId);
  const W = svg.clientWidth || 900, ROW = 26, BAR = 12, LEFT = 58, RIGHT = 46;
  const H = Math.max(1, rows.length) * ROW + 6;
  svg.setAttribute("height", H);
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const max = Math.max(1, ...rows.map((r) => series.reduce((s, [k]) => s + (r.values[k] || 0), 0)));
  const scale = (W - LEFT - RIGHT) / max;
  let out = "";
  rows.forEach((r, i) => {
    const y = i * ROW + 6;
    out += `<text x="${LEFT - 8}" y="${y + BAR - 2}" text-anchor="end" font-size="11" fill="#898781">${r.label}</text>`;
    let x = LEFT, total = 0;
    series.forEach(([k, color]) => {
      const v = r.values[k] || 0;
      total += v;
      if (!v) return;
      const w = Math.max(1.5, v * scale - 2);           // 2px surface gap
      out += `<rect x="${x}" y="${y}" width="${w}" height="${BAR}" rx="3" fill="${color}"/>`;
      x += v * scale;
    });
    out += `<text x="${x + 6}" y="${y + BAR - 2}" font-size="11.5" fill="#ffffff" font-weight="600">${total || ""}</text>`;
  });
  svg.innerHTML = out || "";
  if (!rows.length) svg.innerHTML = `<text x="8" y="20" font-size="12" fill="#898781">no data yet</text>`;
}

function tile(label, value, sub) {
  return `<div class="tile"><div class="t-label">${label}</div><div class="t-value">${value}</div><div class="t-sub">${sub || "&nbsp;"}</div></div>`;
}

async function refresh() {
  let d, s;
  try {
    [d, s] = await Promise.all([
      fetch("/api/metrics/daily").then((r) => r.json()),
      fetch("/api/state").then((r) => r.json()),
    ]);
  } catch { return; }

  document.getElementById("mclock").textContent = s.sim.clock;

  const m = s.metrics;
  const cps = d.kill.find((k) => k.name.startsWith("Cost"));
  document.getElementById("mtiles").innerHTML = [
    tile("people served", d.totals.served, `${m.escalated} with clinical escalation`),
    tile("cost / served", cps && cps.value != null ? "₹" + cps.value : "—", "kit ₹300 + runs ₹120"),
    tile("acceptance", m.acceptance_pct != null ? m.acceptance_pct + "%" : "—", "of orders offered"),
    tile("accept time", m.median_accept_s != null ? Math.round(m.median_accept_s) + "s" : "—", m.p90_accept_s ? `p90 ${Math.round(m.p90_accept_s)}s` : ""),
    tile("open backlog", m.open_cases, "must not grow (kill line)"),
  ].join("");

  document.getElementById("kill-body").innerHTML = d.kill.map((k) => {
    const st = k.ok == null ? ["—", "pend", "awaiting data"] : k.ok ? ["✔", "ok", "healthy"] : ["✘", "bad", "KILL LINE BREACHED"];
    const val = k.value == null ? "—" : (k.name.startsWith("Cost") ? "₹" + k.value : k.value + (k.name.includes("backlog") ? "" : "%"));
    return `<tr><td>${k.name}</td><td class="v">${val}</td><td>${k.target}</td>
      <td class="${st[1]}">${st[0]} ${st[2]}</td></tr>`;
  }).join("");

  stackedBars("chart-cases",
    d.days.map((day) => ({ label: `Day ${day.day}`, values: day.by_category })),
    CATS);
  stackedBars("chart-outcomes",
    d.days.map((day) => ({
      label: `Day ${day.day}`,
      values: { served: day.served, escalated: day.escalated, not_found: day.not_found, declined: day.declined },
    })),
    OUTS);

  document.getElementById("mtable").innerHTML = `<table><tr>
    <th>day</th><th>cases</th><th>medical</th><th>food</th><th>shelter</th>
    <th>served</th><th>escalated</th><th>not found</th><th>declined</th><th>offers</th><th>accepts</th></tr>` +
    d.days.map((x) => `<tr><td>${x.day}</td><td>${x.cases}</td><td>${x.by_category.medical}</td>
      <td>${x.by_category.food}</td><td>${x.by_category.shelter}</td><td>${x.served}</td>
      <td>${x.escalated}</td><td>${x.not_found}</td><td>${x.declined}</td><td>${x.offers}</td><td>${x.accepts}</td></tr>`).join("") +
    "</table>";
}

refresh();
setInterval(refresh, 3000);
