"""Retention purge — privacy by architecture, executed (build plan §4/§5).

media: purged at case close or 72h, whichever first.
lat/lng: nulled at 7 days (the dedup cell key is kept).
case rows: aggregated to coarse cells at 90 days, then deleted.

The dangerous database never exists because this job runs, not because a
policy document says so. `purge(now)` is idempotent and cheap; the API
runs it on a timer and exposes a demo button.
"""

from __future__ import annotations

from .config import Config
from .db import Store


def purge(store: Store, cfg: Config, now: float) -> dict:
    stats = {"media": 0, "latlng": 0, "cases": 0}

    closed = "(SELECT closed_at FROM cases WHERE cases.id = reports.case_id)"
    rows = store.query(
        f"SELECT id FROM reports WHERE media_ref IS NOT NULL AND media_purged=0 AND "
        f"(received_at < ? OR COALESCE({closed}, 1e18) < ?)",
        (now - cfg.media_ttl_s, now))
    for r in rows:
        store.update("reports", r["id"], {"media_ref": None, "media_purged": 1})
    stats["media"] = len(rows)

    rows = store.query(
        "SELECT id FROM cases WHERE lat IS NOT NULL AND created_at < ?",
        (now - cfg.latlng_ttl_s,))
    for r in rows:
        store.update("cases", r["id"], {"lat": None, "lng": None})
    stats["latlng"] = len(rows)

    rows = store.query("SELECT * FROM cases WHERE created_at < ?", (now - cfg.case_row_ttl_s,))
    for r in rows:
        store.execute(
            "INSERT INTO analytics_cells (cell, category, n) VALUES (?, ?, 1) "
            "ON CONFLICT(cell, category) DO UPDATE SET n = n + 1",
            (r["cell"] or "unknown", r["category"] or "unknown"))
        store.execute("DELETE FROM reports WHERE case_id=?", (r["id"],))
        store.execute("DELETE FROM cases WHERE id=?", (r["id"],))
    stats["cases"] = len(rows)
    return stats
