"""Load sanity: 300 cases through the real pipeline, tick under budget,
bounded data structures. Budgets are generous (CI machines vary); the
point is catching quadratic blowups, not micro-benchmarks."""

import time

from pukaar.config import Config
from pukaar.db import Store
from pukaar.service import PukaarService
from pukaar.sim import Sim


def test_300_cases_stay_within_budget():
    cfg = Config()
    cfg.backend = "mock"
    holder = {}
    svc = PukaarService(cfg, Store(":memory:"), now_fn=lambda: holder["sim"].sim_now)
    sim = Sim(svc, cfg, seed=99)
    holder["sim"] = sim
    sim._random_report_at = float("inf")
    sim.speed = 30.0

    # 300 witnesses file reports in bursts while the world keeps ticking
    t_ingest0 = time.perf_counter()
    for i in range(300):
        phone = f"+91-load-{i:04d}"
        svc.wa_inbound(phone, "text", text="ek aadmi bhookha hai station ke paas")
        # ~330m spacing: outside the dedup neighborhood (150m cells, kRing 1),
        # so each report is a distinct person. (At ~90m spacing the dedup
        # correctly merges neighbors — that's the designed trade-off.)
        lat = 28.5933 + ((i % 20) - 10) * 3e-3
        lng = 77.2507 + ((i // 20) - 7) * 3e-3
        svc.wa_inbound(phone, "location", lat=lat, lng=lng)
        svc.wa_inbound(phone, "button", text="fresh:10")
        if i % 10 == 0:
            sim.tick(1.0)
    ingest_s = time.perf_counter() - t_ingest0
    assert ingest_s < 30, f"ingest of 300 cases took {ingest_s:.1f}s"

    cases = svc.store.query("SELECT COUNT(*) n FROM cases")[0]["n"]
    assert cases >= 250        # heavy dedup would mean the grid is too coarse

    # steady-state ticking under load
    times = []
    for _ in range(300):
        t0 = time.perf_counter()
        sim.tick(1.0)
        times.append(time.perf_counter() - t0)
    times.sort()
    mean = sum(times) / len(times)
    p95 = times[int(len(times) * 0.95)]
    assert mean < 0.10, f"mean tick {mean*1000:.1f}ms over budget"
    assert p95 < 0.30, f"p95 tick {p95*1000:.1f}ms over budget"

    # bounded structures: the feed ring, per-order assignment fan-out
    assert len(svc.feed) <= 250
    orders = svc.store.query("SELECT COUNT(*) n FROM orders")[0]["n"]
    asgs = svc.store.query("SELECT COUNT(*) n FROM assignments")[0]["n"]
    assert asgs <= orders * cfg.max_waves * cfg.wave_size_p1, "assignment fan-out unbounded"

    # the system is actually working through the backlog, not seizing up
    served = svc.store.query("SELECT COUNT(*) n FROM outcomes")[0]["n"]
    assert served >= 20, f"only {served} outcomes after sustained ticking"
