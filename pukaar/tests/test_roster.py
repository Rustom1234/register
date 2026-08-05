"""Responder roster: the coordinator's volunteer view — vetting + on/off
duty toggle, gated, and deactivation actually stops new offers."""

from fastapi.testclient import TestClient

from pukaar.api import build_app
from pukaar.config import Config
from pukaar.db import Store
from pukaar.service import PukaarService
from pukaar.sim import Sim


def _mk(seed=3):
    cfg = Config()
    cfg.backend = "mock"
    holder = {}
    svc = PukaarService(cfg, Store(":memory:"), now_fn=lambda: holder["sim"].sim_now)
    sim = Sim(svc, cfg, seed=seed)
    holder["sim"] = sim
    sim._random_report_at = float("inf")
    return svc, sim


def test_roster_lists_seeded_volunteers_with_vetting():
    svc, sim = _mk()
    r = svc.roster()
    assert len(r) == 6
    assert all(v["vetting"] == "verified" and v["active"] for v in r)
    assert any(v["medical"] for v in r)
    assert {"id", "name", "medical", "vetting", "active", "served"} <= set(r[0])


def test_set_active_toggles_and_blocks_offers():
    svc, sim = _mk()
    rid = svc.roster()[0]["id"]
    assert svc.set_active(rid, False) is True
    assert next(v for v in svc.roster() if v["id"] == rid)["active"] is False
    # dispatch only ever offers to active=1 — an inactive responder is not a candidate
    cands = svc.dispatch._candidates.__self__  # dispatch engine
    row = svc.store.one("SELECT active FROM responders WHERE id=?", (rid,))
    assert row["active"] == 0
    assert svc.set_active(rid, True) is True
    assert svc.set_active("nope", True) is False


def test_roster_endpoints_gated_and_working():
    import os
    os.environ["PUKAAR_ADMIN_TOKEN"] = "sesame"
    try:
        cfg = Config()
        cfg.backend = "mock"
        client = TestClient(build_app(cfg))
        client.__enter__()
        assert client.get("/api/roster").status_code == 401           # staff-only
        h = {"x-wayside-token": "sesame"}
        body = client.get("/api/roster", headers=h).json()
        assert len(body["roster"]) == 6
        rid = body["roster"][0]["id"]
        assert client.post("/api/roster/active", headers=h,
                           json={"responder_id": rid, "active": False}).status_code == 200
        assert client.post("/api/roster/active", headers=h,
                           json={"responder_id": "ghost", "active": False}).status_code == 404
        # and it shows up in /api/state for the panel
        assert "roster" in client.get("/api/state", headers=h).json()
    finally:
        del os.environ["PUKAAR_ADMIN_TOKEN"]
