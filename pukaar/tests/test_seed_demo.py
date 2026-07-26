"""The `make demo` boot seed: a photogenic session, ready in seconds."""

from pukaar.config import Config
from pukaar.db import Store
from pukaar.service import PukaarService
from pukaar.sim import Sim


def test_seed_demo_stages_a_recordable_session():
    cfg = Config()
    cfg.backend = "mock"
    holder = {}
    svc = PukaarService(cfg, Store(":memory:"), now_fn=lambda: holder["sim"].sim_now)
    sim = Sim(svc, cfg, seed=42)
    holder["sim"] = sim
    sim._random_report_at = float("inf")

    sim.seed_demo()

    cases = svc.store.query("SELECT * FROM cases")
    assert len(cases) >= 3
    outcomes = svc.store.query("SELECT * FROM outcomes")
    assert len(outcomes) >= 1                      # history exists on boot
    orders = svc.store.query("SELECT * FROM orders")
    assert any(o["status"] in ("accepted", "onsite", "offered", "escalated") for o in orders), \
        "something should be mid-flight for the camera"
    assert sim.golden, "a golden run is staged"
    assert len(svc.feed) >= 8                      # the feed opens populated
