"""The 90-day aggregate cell heatmap: geo.cell_bounds decoding, the
/api/state cells payload, and the seeded demo history."""

from fastapi.testclient import TestClient

from pukaar import geo
from pukaar.api import build_app
from pukaar.config import Config


def test_cell_bounds_round_trip():
    lat, lng = 28.5933, 77.2507                      # Nizamuddin
    key = geo.cell_key(lat, lng)
    south, west, north, east = geo.cell_bounds(key)
    assert south <= lat <= north and west <= lng <= east
    # the bounds' own midpoint maps back to the same cell
    assert geo.cell_key((south + north) / 2, (west + east) / 2) == key
    # cell is ~150 m on each side
    assert 100 < geo.haversine_m(south, west, north, west) < 200
    assert 100 < geo.haversine_m(south, west, south, east) < 200


def test_cell_bounds_rejects_non_grid_keys():
    assert geo.cell_bounds("unknown") is None
    assert geo.cell_bounds("") is None


def test_state_carries_cells_with_bounds():
    cfg = Config()
    cfg.backend = "mock"
    with TestClient(build_app(cfg)) as client:
        svc = client.app.state.svc
        svc.store.execute(
            "INSERT INTO analytics_cells (cell, category, n) VALUES (?, 'food', 3)",
            (geo.cell_key(cfg.zone_lat, cfg.zone_lng),))
        svc.store.execute(
            "INSERT INTO analytics_cells (cell, category, n) VALUES ('unknown', 'medical', 2)")
        cells = client.get("/api/state").json()["cells"]
        assert len(cells) == 1                        # 'unknown' has no bounds
        c = cells[0]
        assert c["n"] == 3 and c["category"] == "food"
        assert c["south"] < cfg.zone_lat < c["north"]
        assert c["west"] < cfg.zone_lng < c["east"]


def test_seed_demo_seeds_aggregate_history():
    cfg = Config()
    cfg.backend = "mock"
    import os
    os.environ["PUKAAR_SEED_DEMO"] = "1"
    try:
        with TestClient(build_app(cfg)) as client:
            cells = client.get("/api/state").json()["cells"]
            assert len(cells) >= 5, "seeded demo should show heatmap history"
            assert any(c["n"] > 1 for c in cells), "hotspots should accumulate counts"
    finally:
        del os.environ["PUKAAR_SEED_DEMO"]
