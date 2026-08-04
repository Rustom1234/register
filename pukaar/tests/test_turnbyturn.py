"""Rider turn-by-turn directions: route_named() carries street names out of
the demo-zone GeoJSON, the sim collapses them into compact {street, m} steps
at accept, and the steps live/die with the order. Runs against the REAL
demo_zone.geojson — the whole point is that the names shown to riders are
the names on the map."""

import json
from pathlib import Path

import pytest

from pukaar import geo
from pukaar.config import Config
from pukaar.db import Store
from pukaar.routing import RoadGraph
from pukaar.service import PukaarService
from pukaar.sim import Sim

DATA = Path(__file__).resolve().parents[1] / "pukaar" / "data" / "demo_zone.geojson"

# Two points ~1.4 km apart across the zone (the basti and east depots) —
# far enough that any route between them must ride several named streets.
WEST = (28.5936, 77.2455)
EAST = (28.5878, 77.2585)


def _mk(seed: int = 42, store: Store | None = None):
    cfg = Config()
    cfg.backend = "mock"
    holder = {}
    svc = PukaarService(cfg, store or Store(":memory:"),
                        now_fn=lambda: holder["sim"].sim_now)
    sim = Sim(svc, cfg, seed=seed)
    holder["sim"] = sim
    sim._random_report_at = float("inf")
    return svc, sim


def _run(sim, sim_seconds, step=5.0):
    t = 0.0
    while t < sim_seconds:
        sim.tick(step / sim.speed)
        t += step


def _enroute_with_steps(svc, sim, budget_s=2400):
    """Drive the sim until some responder is enroute on an accepted order
    with turn-by-turn steps attached."""
    sim.run_scenario("hungry_elder")
    t = 0
    while t < budget_s:
        _run(sim, 20)
        t += 20
        for r in sim._resp.values():
            if r["state"] == "enroute" and r.get("steps"):
                return r
    raise AssertionError("no responder went enroute with steps within budget")


def _geojson_names() -> set[str]:
    fc = json.loads(DATA.read_text(encoding="utf-8"))
    return {f["properties"].get("name") for f in fc["features"]
            if f["properties"].get("kind") == "road"} - {None, ""}


# -------------------------------------------------------- (a) route_named --
def test_route_named_aligns_names_with_waypoints():
    graph = RoadGraph()
    wp, dist_m, dur_s, names = graph.route_named(*WEST, *EAST, mode="scooter")

    assert len(names) == len(wp), "one name per waypoint — the edge leading INTO it"
    assert names[0] == "", "nothing leads into the start"
    assert dist_m > 800, "the depots are well-separated — this is no hop"
    # Every named leg is a real street off the map, and at least one real
    # name shows up (a 1.4 km ride can't be all anonymous galis).
    real = _geojson_names()
    used = {n for n in names if n}
    assert used, "expected at least one named street on a cross-zone route"
    assert used <= real, f"unknown street names: {used - real}"


def test_route_keeps_its_three_tuple_contract():
    # route() delegates to route_named() — existing callers must see the
    # exact same (waypoints, dist, duration) triple as before.
    graph = RoadGraph()
    named = graph.route_named(*WEST, *EAST, mode="cycle")
    assert graph.route(*WEST, *EAST, mode="cycle") == named[:3]


# ------------------------------------------------- (b) collapsed sim steps --
def test_accepted_order_steps_are_compact_and_sum_to_route():
    svc, sim = _mk(seed=7)
    r = _enroute_with_steps(svc, sim)
    steps = r["steps"]

    assert 1 <= len(steps) <= 12
    for st in steps:
        assert isinstance(st["street"], str) and st["street"], "unnamed legs read as 'gali'"
        assert st["m"] >= 0
    total = sim._polyline_m(r["route"])
    assert sum(st["m"] for st in steps) == pytest.approx(total, rel=0.10), \
        "collapsing must conserve the route's metres (± per-step rounding)"
    # the snapshot exposes them to /api/state for the responder app
    view = sim._responder_view(r)
    assert view["steps"] == steps
    assert isinstance(view["step_i"], int) and 0 <= view["step_i"] < len(steps)


# ------------------------------------------------------ (c) close clears --
def test_steps_clear_when_the_order_closes():
    svc, sim = _mk(seed=13)
    r = _enroute_with_steps(svc, sim)
    order_id = r["order_id"]

    assert svc.dispatch.close(order_id, "served") is not None
    sim.settle_kit(order_id, "served")
    _run(sim, 20)   # _sync_states reconciles the external close

    assert r["state"] == "idle" and r["order_id"] is None
    # (r["route"] may already be a fresh idle-wander polyline — that's fine;
    # what must NOT survive is the closed order's direction list.)
    assert r["steps"] is None, \
        "a closed order must not leave stale directions on the rider"
    assert sim._responder_view(r)["steps"] is None


# -------------------------------------------------- collapse cap behavior --
def test_collapse_caps_steps_and_conserves_metres():
    # 30 alternating-name legs of ~60 m: raw steps would be 30 — the cap
    # must fold them to ≤ 8 while keeping the total distance honest.
    lat, lng = 28.5933, 77.2507
    wp, names = [(lat, lng)], [""]
    for i in range(30):
        wp.append(geo.offset_m(*wp[-1], 0.0, 60.0))
        names.append("Ghalib Road" if i % 2 else "Musafir Khana Road")
    steps = Sim._collapse_steps(wp, names)
    assert len(steps) <= 8
    total = sum(geo.haversine_m(*a, *b) for a, b in zip(wp, wp[1:]))
    assert sum(st["m"] for st in steps) == pytest.approx(total, rel=0.02)
