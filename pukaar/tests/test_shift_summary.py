"""Shift handover: the coordinator's end-of-window summary, scoped to
cases opened in the window, served staff-gated as JSON and printable HTML."""

from fastapi.testclient import TestClient

from pukaar.api import build_app
from pukaar.config import Config
from pukaar.db import Store
from pukaar.service import PukaarService
from pukaar.sim import Sim


def _mk(seed: int = 5):
    cfg = Config()
    cfg.backend = "mock"
    holder = {}
    svc = PukaarService(cfg, Store(":memory:"), now_fn=lambda: holder["sim"].sim_now)
    sim = Sim(svc, cfg, seed=seed)
    holder["sim"] = sim
    sim._random_report_at = float("inf")
    return svc, sim


def _report(svc, phone, lat=28.5933, lng=77.2507):
    svc.wa_inbound(phone, "text", text="flyover ke neeche aadmi ghayal hai, khoon")
    svc.wa_inbound(phone, "location", lat=lat, lng=lng)
    svc.wa_inbound(phone, "button", text="fresh:10")


def test_shift_summary_counts_only_window():
    svc, sim = _mk()
    _report(svc, "+91-S1")                       # inside the window
    s = svc.shift_summary(sim.sim_now, hours=12)
    assert s["reports_received"] == 1
    assert s["window_hours"] == 12
    assert "medical" in s["by_category"]

    # a report from 20h ago must fall outside a 12h window
    sim.sim_now += 20 * 3600
    _report(svc, "+91-S2")
    s2 = svc.shift_summary(sim.sim_now, hours=12)
    assert s2["reports_received"] == 1, "the 20h-old case must be excluded"
    s3 = svc.shift_summary(sim.sim_now, hours=48)
    assert s3["reports_received"] == 2, "a wider window includes both"


def test_shift_endpoints_staff_gated_and_render():
    import os
    os.environ["PUKAAR_ADMIN_TOKEN"] = "sesame"
    try:
        cfg = Config()
        cfg.backend = "mock"
        client = TestClient(build_app(cfg))
        client.__enter__()
        # gated without the cookie
        assert client.get("/shift").status_code == 401
        assert client.get("/api/shift").status_code == 401
        h = {"x-wayside-token": "sesame"}
        html = client.get("/shift", headers=h)
        assert html.status_code == 200 and "SHIFT HANDOVER" in html.text
        j = client.get("/api/shift?hours=6", headers=h).json()
        assert j["window_hours"] == 6 and "people_served" in j
        # hours is clamped to a sane range
        assert client.get("/api/shift?hours=999", headers=h).json()["window_hours"] == 72
        assert client.get("/api/shift?hours=0", headers=h).json()["window_hours"] == 1
    finally:
        del os.environ["PUKAAR_ADMIN_TOKEN"]
