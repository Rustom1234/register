"""Retention purge — privacy by architecture, executed (build plan §4/§5).

media: purged at case close or 72h, whichever first.
lat/lng: nulled at 7 days once the case is closed — an open case keeps its
pin, it is the only way to serve it (the dedup cell key is kept).
case rows: closed cases aggregated to coarse cells at 90 days, then
deleted; reports that never became a case (pre-case turns, 112 redirects)
are swept on the same 90-day clock.

The dangerous database never exists because this job runs, not because a
policy document says so. `purge(now)` is idempotent and cheap; the API
runs it on a timer and exposes a demo button.
"""

from __future__ import annotations

from .config import Config
from .db import Store


def purge(store: Store, cfg: Config, now: float) -> dict:
    stats = {"media": 0, "latlng": 0, "cases": 0, "orphan_reports": 0,
             "conversations": 0, "expired": 0}

    # Zombie guard: expires_at is the case's own 72h contract, but nothing
    # enforced it — a case that fell out of every rail kept its pin and
    # landmark text FOREVER, which quietly voids the retention story. Close
    # it (with an audit line) so the normal clocks below start running.
    # Escalated cases are excluded: the clinical follow-up rail owns those.
    rows = store.query(
        "SELECT id FROM cases WHERE status NOT IN ('closed', 'escalated') "
        "AND expires_at IS NOT NULL AND expires_at < ?", (now,))
    for r in rows:
        store.update("cases", r["id"], {"status": "closed", "closed_at": now})
        store.execute(
            "UPDATE orders SET status='closed', closed_at=? "
            "WHERE case_id=? AND status NOT IN ('closed', 'escalated')",
            (now, r["id"]))
        store.audit("system", "case_expired", r["id"], "system", "",
                    "72h expiry — auto-closed by the retention job", ts=now)
    stats["expired"] = len(rows)

    closed = "(SELECT closed_at FROM cases WHERE cases.id = reports.case_id)"
    rows = store.query(
        f"SELECT id FROM reports WHERE media_ref IS NOT NULL AND media_purged=0 AND "
        f"(received_at < ? OR COALESCE({closed}, 1e18) < ?)",
        (now - cfg.media_ttl_s, now))
    for r in rows:
        store.update("reports", r["id"], {"media_ref": None, "media_purged": 1})
    stats["media"] = len(rows)

    # Coordinates are nulled only once the case is finished — an open case's
    # pin is the only way to serve it (and open cases close in hours, not days).
    rows = store.query(
        "SELECT id FROM cases WHERE lat IS NOT NULL AND created_at < ? "
        "AND closed_at IS NOT NULL",
        (now - cfg.latlng_ttl_s,))
    for r in rows:
        store.update("cases", r["id"], {"lat": None, "lng": None})
    stats["latlng"] = len(rows)

    # Same guard on row deletion: never delete an in-flight case out from
    # under its live orders.
    rows = store.query(
        "SELECT * FROM cases WHERE created_at < ? AND closed_at IS NOT NULL",
        (now - cfg.case_row_ttl_s,))
    for r in rows:
        store.execute(
            "INSERT INTO analytics_cells (cell, category, n) VALUES (?, ?, 1) "
            "ON CONFLICT(cell, category) DO UPDATE SET n = n + 1",
            (r["cell"] or "unknown", r["category"] or "unknown"))
        store.execute("DELETE FROM reports WHERE case_id=?", (r["id"],))
        store.execute("DELETE FROM cases WHERE id=?", (r["id"],))
    stats["cases"] = len(rows)

    # Reports that never became a case (pre-case turns, 112 redirects) hold
    # raw witness text + reporter hash; sweep them on the same 90-day clock.
    orphans = store.query(
        "SELECT id FROM reports WHERE (case_id IS NULL "
        "OR case_id NOT IN (SELECT id FROM cases)) AND received_at < ?",
        (now - cfg.case_row_ttl_s,))
    for r in orphans:
        store.execute("DELETE FROM reports WHERE id=?", (r["id"],))
    stats["orphan_reports"] = len(orphans)

    # Idle conversations hold raw witness chat; forget them at 30 days.
    idle = store.query("SELECT phone FROM conversations WHERE updated_at < ?",
                       (now - cfg.conversation_ttl_s,))
    for r in idle:
        store.execute("DELETE FROM conversations WHERE phone=?", (r["phone"],))
    stats["conversations"] = len(idle)
    return stats
