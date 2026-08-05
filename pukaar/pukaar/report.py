"""Printable session report — a clean handout served at /report.

Light theme on purpose: it's for print/PDF after a demo or a field day.
Everything comes from the store; no live JS, no external assets.
"""

from __future__ import annotations

import html

from . import strings


def _fmt_t(ts: float | None) -> str:
    if ts is None:
        return "—"
    d = int(ts // 86400)
    return f"D{d} {int(ts % 86400 // 3600):02d}:{int(ts % 3600 // 60):02d}"


def render_report(svc, sim) -> str:
    m = svc.metrics()
    daily = svc.daily_metrics()
    cases = svc.store.query("SELECT * FROM cases ORDER BY created_at")
    orders = {o["case_id"]: o for o in svc.store.query("SELECT * FROM orders")}
    outcomes = {o["case_id"]: o for o in svc.store.query("SELECT * FROM outcomes")}

    def outcome_label(cid: str) -> str:
        o = outcomes.get(cid)
        if not o:
            return "open"
        if o["escalated"]:
            done = "completed" if o["escalation_completed_at"] else "pending"
            return f"served + clinical ({done})"
        if o["served"]:
            return "served"
        if not o["found"]:
            return "withdrawn (witness)" if o["closed_by"] == "witness" else "not found"
        return "declined (respected)"

    rows = "".join(
        f"<tr><td>{html.escape(c['id'][-4:].upper())}</td>"
        f"<td>{html.escape(c['category'] or '—')}</td>"
        f"<td>{(orders.get(c['id']) or {}).get('priority', '—')}</td>"
        f"<td>{'🩺' if (orders.get(c['id']) or {}).get('clinical_flag') else ''}</td>"
        f"<td>{c['merged_witnesses']}</td>"
        f"<td>{_fmt_t(c['created_at'])}</td>"
        f"<td>{_fmt_t(c['closed_at'])}</td>"
        f"<td>{outcome_label(c['id'])}</td></tr>"
        for c in cases)

    kill_rows = "".join(
        f"<tr><td>{k['name']}</td><td>{'—' if k['value'] is None else k['value']}</td>"
        f"<td>{k['target']}</td>"
        f"<td class={'ok' if k['ok'] else 'pend' if k['ok'] is None else 'bad'}>"
        f"{'✔ healthy' if k['ok'] else '— pending' if k['ok'] is None else '✘ breached'}</td></tr>"
        for k in daily["kill"])

    kits = " · ".join(f"{sku} {n}" for sku, n in m["kits"].items())
    lang_counts: dict[str, int] = {}
    for conv in list(svc.conversations.values()):
        lang = conv.state.get("lang", "hinglish")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    lang_mix = " · ".join(f"{k} {v}" for k, v in sorted(lang_counts.items())) or "—"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Wayside — session report</title>
<style>
  body {{ font-family: system-ui, sans-serif; color: #0b0b0b; background: #fff;
         max-width: 880px; margin: 0 auto; padding: 32px 24px; font-size: 14px; }}
  h1 {{ font-size: 20px; letter-spacing: 0.12em; margin: 0; }}
  .sub {{ color: #52514e; margin: 4px 0 22px; }}
  .tiles {{ display: flex; gap: 24px; flex-wrap: wrap; margin: 18px 0 26px; }}
  .tile b {{ display: block; font-size: 24px; }}
  .tile span {{ color: #52514e; font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; }}
  table {{ border-collapse: collapse; width: 100%; margin: 10px 0 24px; }}
  th {{ text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em;
       color: #52514e; border-bottom: 2px solid #0b0b0b; padding: 6px 8px; }}
  td {{ border-bottom: 1px solid #e1e0d9; padding: 6px 8px; }}
  .ok {{ color: #006300; font-weight: 600; }} .bad {{ color: #d03b3b; font-weight: 700; }}
  .pend {{ color: #898781; }}
  h2 {{ font-size: 13px; letter-spacing: 0.1em; text-transform: uppercase; margin: 26px 0 4px; }}
  .foot {{ color: #52514e; font-size: 12px; border-top: 1px solid #e1e0d9;
           margin-top: 28px; padding-top: 12px; }}
  @media print {{ body {{ padding: 0; }} .noprint {{ display: none; }} }}
</style></head><body>
<h1>WAYSIDE · SESSION REPORT</h1>
<div class="sub">Nizamuddin pilot zone (demo) · generated {sim._clock_str()} ·
backend: {svc.backend.name} · <span class="noprint"><a href="/">back to control room</a> ·
print this page for the handout</span></div>

<div class="tiles">
  <div class="tile"><b>{daily['totals']['served']}</b><span>people served</span></div>
  <div class="tile"><b>{m['escalated']}</b><span>clinical escalations</span></div>
  <div class="tile"><b>{m['acceptance_pct'] if m['acceptance_pct'] is not None else '—'}%</b><span>offer acceptance</span></div>
  <div class="tile"><b>{m['median_accept_s'] or '—'}s</b><span>median accept</span></div>
  <div class="tile"><b>{m['open_cases']}</b><span>open backlog</span></div>
</div>

<h2>Pre-registered kill criteria</h2>
<table><tr><th>Criterion</th><th>Now</th><th>Target</th><th>Status</th></tr>{kill_rows}</table>

<h2>Cases</h2>
<table><tr><th>ID</th><th>Category</th><th>Priority</th><th></th><th>Witnesses</th>
<th>Reported</th><th>Closed</th><th>Outcome</th></tr>{rows}</table>

<h2>Kits remaining</h2>
<p>{kits or '—'} (partner_1)</p>

<h2>Witness languages (auto-mirrored)</h2>
<p>{lang_mix}</p>

<div class="foot">
Witness reports and agent inferences are HMAC provenance-tagged; responder observations
and system actions carry provenance labels in the audit log.
Privacy by architecture: no identities of street residents are stored; photos delete at
case close; exact locations null 7 days after a case closes (open cases keep their pin
until served); closed rows aggregate to coarse cells at 90 days, when reports that never
became a case are swept too.
Emergency messages are fixed strings — no model ever speaks in the 112 path.
Kit SKUs: {', '.join(f"{k} ({v['name']})" for k, v in strings.KIT_SKUS.items())}.
</div>
</body></html>"""


def render_shift(s: dict, hours: float) -> str:
    """Printable end-of-shift handover for a coordinator — one page, plain
    language, light theme for print. All numbers scoped to the window."""
    def _hm(sec):
        if sec is None:
            return "—"
        return f"{int(sec // 60)}m {int(sec % 60)}s" if sec >= 60 else f"{int(sec)}s"

    cats = s["by_category"]
    cat_rows = "".join(
        f"<tr><td>{html.escape(k)}</td><td>{v}</td></tr>"
        for k, v in sorted(cats.items(), key=lambda kv: -kv[1])) or "<tr><td>—</td><td>0</td></tr>"
    low = ", ".join(html.escape(x) for x in s["low_stock_skus"]) or "none"
    kits = ", ".join(f"{html.escape(k)}: {v}" for k, v in s["kits_on_hand"].items()) or "—"
    d = int(s["generated_sim"] // 86400)
    clock = f"D{d} {int(s['generated_sim'] % 86400 // 3600):02d}:{int(s['generated_sim'] % 3600 // 60):02d}"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Wayside — shift handover</title>
<style>
  body {{ font: 15px/1.6 system-ui, -apple-system, sans-serif; color: #1a1c22;
    max-width: 720px; margin: 40px auto; padding: 0 20px; }}
  h1 {{ font-size: 22px; letter-spacing: 0.06em; margin: 0; }}
  .sub {{ color: #6f6d66; margin: 2px 0 24px; }}
  .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin: 0 0 26px; }}
  .stat {{ border: 1px solid #e3e0d8; border-radius: 10px; padding: 14px 16px; }}
  .stat b {{ display: block; font-size: 28px; font-variant-numeric: tabular-nums; }}
  .stat.hero b {{ color: #177a43; }}
  .stat span {{ color: #6f6d66; font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; }}
  h2 {{ font-size: 13px; letter-spacing: 0.08em; text-transform: uppercase; color: #6f6d66;
    border-bottom: 1px solid #e3e0d8; padding-bottom: 6px; margin: 26px 0 10px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  td {{ padding: 5px 8px; border-bottom: 1px solid #efece5; }}
  td:last-child {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .foot {{ color: #8b8983; font-size: 12px; margin-top: 30px; border-top: 1px solid #e3e0d8; padding-top: 12px; }}
  @media print {{ body {{ margin: 0; }} }}
</style></head><body>
<h1>WAYSIDE · SHIFT HANDOVER</h1>
<p class="sub">Last {int(hours)} hours · generated {clock} (sim time)</p>

<div class="grid">
  <div class="stat hero"><b>{s['people_served']}</b><span>people served</span></div>
  <div class="stat"><b>{s['reports_received']}</b><span>reports received</span></div>
  <div class="stat"><b>{s['clinical_escalations']}</b><span>clinical escalations</span></div>
  <div class="stat"><b>{s['still_open_at_handover']}</b><span>still open — hand to next shift</span></div>
  <div class="stat"><b>{_hm(s['median_accept_s'])}</b><span>median time to accept</span></div>
  <div class="stat"><b>{s['not_found']}</b><span>person had moved on</span></div>
</div>

<h2>Reports by need</h2>
<table>{cat_rows}</table>

<h2>Kit movement this shift</h2>
<table>
  <tr><td>Kits delivered</td><td>{s['kits_delivered']}</td></tr>
  <tr><td>Returned unused (person not found)</td><td>{s['kits_returned_unused']}</td></tr>
  <tr><td>Courier restocks received (recent)</td><td>{s['courier_restocks']}</td></tr>
</table>

<h2>Stock at handover</h2>
<p>{kits}<br><b>Low / reorder:</b> {low}</p>

<div class="foot">
Privacy by architecture: no identities of street residents are stored; photos delete at
case close; exact pins null 7 days after close. This handover is a live snapshot — print
or save it at the end of a shift. Numbers cover cases opened in the window only.
</div>
</body></html>"""
