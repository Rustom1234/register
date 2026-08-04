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
