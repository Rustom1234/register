"""End-to-end: scenarios through the REAL pipeline plus the sim's responders.

This is the demo's backbone — witness report -> intake -> case -> order ->
wave -> accept -> travel -> outcome -> closure message — with time fully
under test control.
"""

from pukaar.config import Config
from pukaar.db import Store
from pukaar.service import PukaarService
from pukaar.sim import Sim


def _mk():
    cfg = Config()
    cfg.backend = "mock"
    holder = {}
    svc = PukaarService(cfg, Store(":memory:"), now_fn=lambda: holder["sim"].sim_now)
    sim = Sim(svc, cfg, seed=42)
    holder["sim"] = sim
    sim._random_report_at = float("inf")   # deterministic: no random reports
    return cfg, svc, sim


def _run(sim, sim_seconds, step=5.0):
    t = 0.0
    while t < sim_seconds:
        sim.tick(step / sim.speed)
        t += step


def test_scenario_reaches_closure():
    cfg, svc, sim = _mk()
    sim.run_scenario("injured_flyover")

    assert len(svc.store.query("SELECT * FROM cases")) == 1
    order = svc.store.one("SELECT * FROM orders")
    assert order["sku"] == "MED-1" and order["clinical_flag"] == 1

    _run(sim, 3 * 3600)  # three sim-hours is plenty for accept+travel+close

    order = svc.store.one("SELECT * FROM orders")
    assert order["status"] in ("closed", "escalated"), order["status"]
    outs = svc.store.query("SELECT * FROM outcomes")
    assert len(outs) == 1

    # the witness got a closure message (fixed string, never generated)
    conv = list(svc.conversations.values())[0]
    bot_msgs = [m["text"] for m in conv.log if m["from"] == "bot"]
    assert any("Aapki report" in m for m in bot_msgs)


def test_duplicate_burst_merges_to_one_case():
    cfg, svc, sim = _mk()
    sim.run_scenario("duplicate_burst")
    cases = svc.store.query("SELECT * FROM cases")
    assert len(cases) == 1
    assert cases[0]["merged_witnesses"] == 3
    assert len(svc.store.query("SELECT * FROM orders")) == 1


def test_emergency_scenario_never_creates_case():
    cfg, svc, sim = _mk()
    sim.run_scenario("emergency_112")
    assert svc.store.query("SELECT * FROM cases") == []
    conv = list(svc.conversations.values())[0]
    assert any("112" in m["text"] for m in conv.log if m["from"] == "bot")


def test_many_scenarios_stay_consistent():
    cfg, svc, sim = _mk()
    for name in ("injured_flyover", "family_rain", "hungry_elder"):
        sim.run_scenario(name)
    _run(sim, 6 * 3600)
    orders = svc.store.query("SELECT * FROM orders")
    assert all(o["status"] in ("closed", "escalated", "needs_coordinator", "offered", "accepted", "onsite")
               for o in orders)
    m = svc.metrics()
    assert m["served"] + m["escalated"] >= 1
    # acceptance metric is populated once offers happened
    assert m["acceptance_pct"] is None or 0 <= m["acceptance_pct"] <= 100
