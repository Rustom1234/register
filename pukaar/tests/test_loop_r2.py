"""Round-2 loop regressions: favicon route + staff-gate openness.

The browser asks for /favicon.ico unprompted on every page, including the
bare /login screen of a token-protected deploy — it must resolve without a
cookie and serve the real app icon, not a 404.
"""
from fastapi.testclient import TestClient

from pukaar.api import build_app
from pukaar.config import Config


def _client():
    cfg = Config()
    cfg.backend = "mock"
    client = TestClient(build_app(cfg))
    client.__enter__()
    return client


def test_favicon_served_as_png():
    client = _client()
    r = client.get("/favicon.ico")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_favicon_open_through_staff_gate():
    import os
    os.environ["PUKAAR_ADMIN_TOKEN"] = "sesame"
    try:
        cfg = Config()
        cfg.backend = "mock"
        client = TestClient(build_app(cfg))
        client.__enter__()
        assert client.get("/supervisor").status_code == 401      # gate is live
        assert client.get("/favicon.ico").status_code == 200     # icon stays open
    finally:
        del os.environ["PUKAAR_ADMIN_TOKEN"]


def test_witness_surface_public_on_token_deploy():
    """The P1 from R14: on a staff-token deploy the witness page, its
    assets, and its scoped data feed must stay reachable — control-room
    surfaces and the full /api/state must not."""
    import os
    os.environ["PUKAAR_ADMIN_TOKEN"] = "sesame"
    try:
        cfg = Config()
        cfg.backend = "mock"
        client = TestClient(build_app(cfg))
        client.__enter__()
        # public witness surface — no cookie needed
        assert client.get("/witness").status_code == 200
        assert client.get("/api/witness/state", params={"phone": "+91-DEMO"}).status_code == 200
        assert client.get("/static/app.css").status_code == 200
        assert client.get("/data/demo_zone.geojson").status_code == 200
        assert client.get("/sw.js").status_code == 200
        # the scoped feed leaks nothing but the caller's own thread + zone
        body = client.get("/api/witness/state", params={"phone": "+91-XYZ"}).json()
        assert set(body) == {"zone", "conversations"}
        assert "cases" not in body and "sim" not in body
        # staff surfaces stay gated
        assert client.get("/").status_code == 401
        assert client.get("/supervisor").status_code == 401
        assert client.get("/api/state").status_code == 401
        assert client.get("/shift").status_code == 401
    finally:
        del os.environ["PUKAAR_ADMIN_TOKEN"]
