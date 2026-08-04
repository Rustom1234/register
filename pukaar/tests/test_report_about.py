"""The /report handout and the about page routes."""

from fastapi.testclient import TestClient

from pukaar.api import build_app
from pukaar.config import Config


def _client():
    cfg = Config()
    cfg.backend = "mock"
    return TestClient(build_app(cfg))


def test_report_renders_with_kill_criteria():
    with _client() as client:
        client.post("/api/scenario/hungry_elder")
        r = client.get("/report")
        assert r.status_code == 200
        body = r.text
        assert "SESSION REPORT" in body
        assert "kill criteria" in body.lower()
        assert "Verified-need rate" in body
        assert "provenance-tagged" in body

def test_about_page_served():
    with _client() as client:
        r = client.get("/static/about.html")
        assert r.status_code == 200
        assert "Wayside" in r.text
        assert "Honest limits" in r.text


def test_state_exposes_golden_orders():
    with _client() as client:
        client.post("/api/scenario/golden_run")
        s = client.get("/api/state").json()
        assert isinstance(s["sim"]["golden"], list)
        assert len(s["sim"]["golden"]) == 1
