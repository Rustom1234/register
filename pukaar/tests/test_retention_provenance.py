"""Retention purge and provenance signing — privacy by architecture, tested."""

from pukaar.db import new_id
from pukaar.provenance import Provenance
from pukaar.retention import purge


def _old_case(svc, created_at, with_media=True, lat=28.59):
    cid = new_id("case")
    svc.store.insert("cases", {
        "id": cid, "status": "closed", "category": "food", "category_conf": 1.0,
        "urgency": "medium", "cell": "c:1", "lat": lat, "lng": 77.25, "geo_conf": "pin",
        "landmark_text": None, "freshness_min": 5, "detail": "d", "merged_witnesses": 1,
        "created_at": created_at, "closed_at": created_at + 5, "expires_at": None,
    })
    if with_media:
        svc.store.insert("reports", {
            "id": new_id("rep"), "case_id": cid, "reporter_hash": "h", "lang": "hi",
            "body": "b", "media_ref": "m", "media_purged": 0,
            "received_at": created_at, "provenance": "witness", "hmac": "x",
        })
    return cid


def test_media_purged_after_close(svc, clock, cfg):
    _old_case(svc, created_at=clock() - 10)   # closed in the past
    stats = purge(svc.store, cfg, clock() + 1)
    assert stats["media"] == 1
    rep = svc.store.one("SELECT * FROM reports")
    assert rep["media_ref"] is None and rep["media_purged"] == 1


def test_latlng_nulled_after_7_days(svc, clock, cfg):
    cid = _old_case(svc, created_at=clock() - cfg.latlng_ttl_s - 5, with_media=False)
    purge(svc.store, cfg, clock())
    case = svc.store.one("SELECT * FROM cases WHERE id=?", (cid,))
    assert case["lat"] is None and case["lng"] is None
    assert case["cell"] == "c:1"              # coarse cell survives for analytics


def test_case_rows_aggregate_after_90_days(svc, clock, cfg):
    _old_case(svc, created_at=clock() - cfg.case_row_ttl_s - 5)
    purge(svc.store, cfg, clock())
    assert svc.store.query("SELECT * FROM cases") == []
    assert svc.store.query("SELECT * FROM reports") == []
    agg = svc.store.one("SELECT * FROM analytics_cells WHERE cell='c:1' AND category='food'")
    assert agg["n"] == 1


def test_purge_idempotent(svc, clock, cfg):
    _old_case(svc, created_at=clock() - cfg.case_row_ttl_s - 5)
    purge(svc.store, cfg, clock())
    stats2 = purge(svc.store, cfg, clock())
    # media_orphans appears only when a media dir exists to scan; the second
    # purge does no NEW work regardless, so every count is zero.
    assert all(v == 0 for v in stats2.values())
    assert {"media", "latlng", "cases", "orphan_reports", "conversations",
            "expired"} <= set(stats2)


def test_provenance_sign_verify_and_tamper():
    p = Provenance("k" * 32)
    payload = {"sku": "MED-1", "priority": "P2"}
    mac = p.sign("agent_inferred", payload)
    assert p.verify("agent_inferred", payload, mac)
    assert not p.verify("witness", payload, mac)            # channel swap detected
    assert not p.verify("agent_inferred", {**payload, "priority": "P3"}, mac)  # tamper detected


def test_provenance_rejects_unknown_channel():
    p = Provenance("k" * 32)
    try:
        p.sign("nonsense", {})
        raise AssertionError("should have raised")
    except ValueError:
        pass
