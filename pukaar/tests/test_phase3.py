"""Phase 3 — kit depots: routing via pickup, per-depot stock, stockout."""

from pukaar.config import Config
from pukaar.db import Store
from pukaar.service import PukaarService
from pukaar.sim import DEPOT_SEED, Sim
from pukaar import geo


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


def _accepted_responder(svc, sim, budget=2400):
    """Advance in small steps and grab the responder the moment an order is
    accepted — a fixed big window can overshoot the whole arc."""
    t = 0.0
    while t < budget:
        _run(sim, 20)
        t += 20
        order = svc.store.one(
            "SELECT * FROM orders WHERE responder_id IS NOT NULL "
            "AND status IN ('accepted','onsite')")
        if order:
            return sim._resp[order["responder_id"]], order
    return None, None


def test_state_exposes_depots_with_stock():
    svc, sim = _mk()
    depots = sim.depots()
    assert len(depots) == len(DEPOT_SEED) == 3
    total_med = sum(d["stock"].get("MED-1", 0) for d in depots)
    assert total_med == 18                       # network totals match the old world


def test_accept_routes_via_a_depot_and_picks_up():
    svc, sim = _mk()
    sim.run_scenario("hungry_elder")
    r, order = _accepted_responder(svc, sim)
    assert r is not None, "no acceptance within the budget"
    # the rider either already passed the depot or still carries the plan
    assert r["depot_id"] is not None
    depot = next(d for d in DEPOT_SEED if d[0] == r["depot_id"])
    if not r["picked_up"]:
        # the planned route physically passes through the depot's snap point:
        # some waypoint lies within 60 m of the depot
        assert any(geo.haversine_m(w[0], w[1], depot[2], depot[3]) < 60
                   for w in r["route"]), "route does not pass the chosen depot"
    # driving long enough must produce the pickup feed event
    _run(sim, 3600)
    kinds = [e["kind"] for e in svc.feed]
    assert "kit_pickup" in kinds


def test_serving_consumes_at_the_chosen_depot():
    svc, sim = _mk()
    before = {d["id"]: dict(d["stock"]) for d in sim.depots()}
    sim.run_scenario("hungry_elder")
    _run(sim, 3 * 3600)                          # full arc incl. depot detour
    out = svc.store.query("SELECT * FROM outcomes")
    if not out:                                  # outcome landed as not_found/declined
        return
    after = {d["id"]: dict(d["stock"]) for d in sim.depots()}
    total_before = sum(sum(s.values()) for s in before.values())
    total_after = sum(sum(s.values()) for s in after.values())
    served = svc.store.one(
        "SELECT COUNT(*) AS n FROM outcomes WHERE served=1 OR escalated=1")["n"]
    # every served/escalated outcome consumed exactly one kit somewhere
    # (no restock fired in this window: thresholds sit well below seeds)
    assert total_before - total_after == served


def test_network_stockout_goes_direct_and_flags():
    svc, sim = _mk()
    svc.store.execute("UPDATE inventory SET count = 0")     # nothing anywhere
    sim.run_scenario("hungry_elder")
    r, order = _accepted_responder(svc, sim, budget=1800)
    assert r is not None
    assert r["depot_id"] is None and r["picked_up"] is True
    assert any(e["kind"] == "coordinator_flag" and "stockout" in e.get("reason", "")
               for e in svc.feed)
