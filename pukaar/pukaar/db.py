"""SQLite store — the domain record (build plan §4).

Kinetic sim state (live responder positions) stays in memory; everything
that is a *record* — reports, cases, orders, assignments, outcomes,
roster, inventory, audit — lives here, with the retention columns the
purge job enforces. One writer lock; WAL; dict rows.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
  id TEXT PRIMARY KEY, case_id TEXT, reporter_hash TEXT, lang TEXT,
  body TEXT, media_ref TEXT, media_purged INTEGER DEFAULT 0,
  received_at REAL, provenance TEXT, hmac TEXT
);
CREATE TABLE IF NOT EXISTS cases (
  id TEXT PRIMARY KEY, status TEXT, category TEXT, category_conf REAL,
  urgency TEXT, cell TEXT, lat REAL, lng REAL, geo_conf TEXT,
  landmark_text TEXT, freshness_min INTEGER, detail TEXT,
  merged_witnesses INTEGER DEFAULT 1, recheck_sent INTEGER DEFAULT 0,
  created_at REAL, closed_at REAL, expires_at REAL
);
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY, case_id TEXT, sku TEXT, addons TEXT,
  clinical_flag INTEGER, priority TEXT, instruction_ids TEXT,
  partner_id TEXT, status TEXT, created_by TEXT, confidence REAL,
  wave INTEGER DEFAULT 0, responder_id TEXT,
  created_at REAL, accepted_at REAL, arrived_at REAL, closed_at REAL, hmac TEXT
);
CREATE TABLE IF NOT EXISTS assignments (
  id TEXT PRIMARY KEY, order_id TEXT, responder_id TEXT,
  offered_at REAL, responded_at REAL, response TEXT
);
CREATE TABLE IF NOT EXISTS outcomes (
  id TEXT PRIMARY KEY, case_id TEXT, found INTEGER, served INTEGER,
  person_accepted INTEGER, escalated INTEGER, escalation_completed_at REAL,
  closed_by TEXT, created_at REAL
);
CREATE TABLE IF NOT EXISTS responders (
  id TEXT PRIMARY KEY, partner_id TEXT, display_name TEXT,
  medical INTEGER DEFAULT 0, vetting TEXT DEFAULT 'verified', active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS inventory (
  partner_id TEXT, sku TEXT, count INTEGER, restock_threshold INTEGER DEFAULT 6,
  PRIMARY KEY (partner_id, sku)
);
CREATE TABLE IF NOT EXISTS audit_log (
  id TEXT PRIMARY KEY, ts REAL, actor TEXT, action TEXT,
  object_id TEXT, provenance TEXT, hmac TEXT, detail TEXT
);
CREATE TABLE IF NOT EXISTS analytics_cells (
  cell TEXT, category TEXT, n INTEGER, PRIMARY KEY (cell, category)
);
"""


def _rows(cur: sqlite3.Cursor) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


class Store:
    def __init__(self, path: str = ":memory:"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._lock = threading.RLock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # -- generic helpers -------------------------------------------------
    def execute(self, sql: str, params: tuple = ()) -> None:
        with self._lock:
            self._conn.execute(sql, params)
            self._conn.commit()

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return _rows(cur)

    def one(self, sql: str, params: tuple = ()) -> dict | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def insert(self, table: str, row: dict) -> None:
        keys = ", ".join(row)
        marks = ", ".join("?" for _ in row)
        vals = tuple(json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for v in row.values())
        self.execute(f"INSERT OR REPLACE INTO {table} ({keys}) VALUES ({marks})", vals)

    def update(self, table: str, obj_id: str, patch: dict) -> None:
        sets = ", ".join(f"{k}=?" for k in patch)
        vals = tuple(json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for v in patch.values())
        self.execute(f"UPDATE {table} SET {sets} WHERE id=?", vals + (obj_id,))

    def audit(self, actor: str, action: str, object_id: str, provenance: str = "system",
              mac: str = "", detail: str = "", ts: float | None = None) -> None:
        self.insert("audit_log", {
            "id": new_id("aud"), "ts": ts if ts is not None else time.time(),
            "actor": actor, "action": action, "object_id": object_id,
            "provenance": provenance, "hmac": mac, "detail": detail,
        })


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"
