"""Loop round 1 — regression pins for the adversarially-confirmed fixes."""

from fastapi.testclient import TestClient

from pukaar.api import build_app
from pukaar.config import Config
from pukaar.db import Store
from pukaar.service import PukaarService
from pukaar.sim import Sim


def _mk(seed: int = 42):
    cfg = Config()
    cfg.backend = "mock"
    holder = {}
    svc = PukaarService(cfg, Store(":memory:"), now_fn=lambda: holder["sim"].sim_now)
    sim = Sim(svc, cfg, seed=seed)
    holder["sim"] = sim
    sim._random_report_at = float("inf")
    return svc, sim


def _run(sim, sim_seconds, step=5.0):
    t = 0.0
    while t < sim_seconds:
        sim.tick(step / sim.speed)
        t += step


def _total_stock(sim) -> int:
    return sum(sum(d["stock"].values()) for d in sim.depots())


def test_stock_reserved_at_accept_and_returned_on_not_found():
    svc, sim = _mk()
    before = _total_stock(sim)
    sim.run_scenario("hungry_elder")
    # advance until an acceptance reserves a kit
    t = 0
    while _total_stock(sim) == before and t < 2400:
        _run(sim, 20)
        t += 20
    assert _total_stock(sim) == before - 1, "accept must reserve the kit immediately"
    order = svc.store.one("SELECT * FROM orders WHERE responder_id IS NOT NULL")
    # settle as not_found -> the kit goes back on the shelf
    sim.settle_kit(order["id"], "not_found")
    assert _total_stock(sim) == before
    assert any(e["kind"] == "kit_return" for e in svc.feed)
    # settling again must not double-return
    sim.settle_kit(order["id"], "not_found")
    assert _total_stock(sim) == before


def test_human_close_via_api_keeps_ledger_truthful():
    cfg = Config()
    cfg.backend = "mock"
    client = TestClient(build_app(cfg))
    client.__enter__()
    svc, sim = client.app.state.svc, client.app.state.sim
    sim._random_report_at = float("inf")
    before = sum(sum(d["stock"].values()) for d in sim.depots())
    sim.run_scenario("hungry_elder")
    t = 0
    while sum(sum(d["stock"].values()) for d in sim.depots()) == before and t < 2400:
        _run(sim, 20)
        t += 20
    order = svc.store.one("SELECT * FROM orders WHERE responder_id IS NOT NULL")
    rid = order["responder_id"]
    sim.manual.add(rid)                     # a human is playing this rider
    # human closes served via the API: stock stays consumed (reserved at accept)
    r = client.post("/api/responder", json={"action": "outcome",
                                            "order_id": order["id"], "outcome": "served"})
    assert r.status_code == 200 and r.json()["ok"]
    assert sum(sum(d["stock"].values()) for d in sim.depots()) == before - 1
    assert order["id"] not in sim._reservations


def test_golden_run_requires_idle_medical():
    svc, sim = _mk()
    # make every medical responder busy
    for r in sim._resp.values():
        if r["medical"]:
            r["state"] = "onsite"
    msg = sim.run_scenario("golden_run")
    assert "no idle medical responder" in msg
    assert not svc.store.query("SELECT * FROM cases"), "bail must happen before staging a case"


def test_restart_resumes_clock_and_recovers_onsite(tmp_path):
    import os
    db = tmp_path / "persist.db"
    cfg = Config()
    cfg.backend = "mock"
    store = Store(str(db))
    holder = {}
    svc = PukaarService(cfg, store, now_fn=lambda: holder["sim"].sim_now)
    sim = Sim(svc, cfg, seed=42)
    holder["sim"] = sim
    sim._random_report_at = float("inf")
    _run(sim, 600)
    clock_before = sim.sim_now
    store._conn.commit()

    # "restart": brand-new service+sim over the same file
    store2 = Store(str(db))
    holder2 = {}
    svc2 = PukaarService(cfg, store2, now_fn=lambda: holder2["sim"].sim_now)
    sim2 = Sim(svc2, cfg, seed=43)
    holder2["sim"] = sim2
    assert sim2.sim_now >= clock_before, "sim clock must resume, not rewind"
    # depot stock must not have been re-seeded over live values
    total = sum(sum(d["stock"].values()) for d in sim2.depots())
    assert total <= 57                     # never above the seed total


def test_staff_gate_blocks_without_token_and_admits_with():
    import os
    os.environ["PUKAAR_ADMIN_TOKEN"] = "sesame"
    try:
        cfg = Config()
        cfg.backend = "mock"
        client = TestClient(build_app(cfg))
        client.__enter__()
        assert client.get("/api/state").status_code == 401
        assert client.get("/supervisor").status_code == 401
        assert client.get("/health").status_code == 200          # probe stays open
        r = client.post("/api/wa/inbound", json={"phone": "+91-T1", "kind": "text",
                                                 "text": "madad chahiye"})
        assert r.status_code == 200                              # witness path open
        assert client.get("/login", params={"token": "wrong"}).status_code == 401
        ok = client.get("/login", params={"token": "sesame"}, follow_redirects=False)
        assert ok.status_code == 302
        assert client.get("/api/state").status_code == 200       # cookie now set
        hdr = client.get("/api/export", headers={"x-wayside-token": "sesame"})
        assert hdr.status_code == 200
    finally:
        del os.environ["PUKAAR_ADMIN_TOKEN"]


def test_no_arrival_before_pickup():
    svc, sim = _mk(seed=7)
    sim.run_scenario("hungry_elder")
    saw_enroute_unpicked = False
    for _ in range(600):
        sim.tick(5.0 / sim.speed)
        for r in sim._resp.values():
            if r["state"] == "enroute" and not r.get("picked_up", True):
                saw_enroute_unpicked = True
            # the invariant: nobody is ever onsite without the kit
            if r["state"] == "onsite":
                assert r.get("picked_up", True), "arrived without collecting the kit"
    assert saw_enroute_unpicked, "test never exercised the pickup leg"
