"""The wider city around the pilot zone, and the data the map needs to make
riders glide.

demo_city.geojson is procedurally generated scenery (tools/make_city_surrounds.py)
so that panning or zooming out shows streets instead of a void. Two things
must stay true forever:

  * it is SCENERY. The router builds its graph from demo_zone.geojson alone,
    so nothing here can ever put a rider on an invented street.
  * it never overdraws the hand-built pilot zone, and it stays small enough
    to ship on every page load.

The responder payload's speed_mps is the other half of the smooth-motion
work: the map dead-reckons between 1 Hz polls with exactly this number, so
it has to be the same figure the sim moves the rider by.
"""

import json
import math
from pathlib import Path

import pytest

from pukaar import routing
from pukaar.config import Config
from pukaar.db import Store
from pukaar.service import PukaarService
from pukaar.sim import MODE_SPEED_MPS, Sim

DATA = Path(__file__).resolve().parents[1] / "pukaar" / "data"
CITY = DATA / "demo_city.geojson"
ZONE = DATA / "demo_zone.geojson"
STATIC = Path(__file__).resolve().parents[1] / "pukaar" / "static"

ROAD_CLASSES = {"primary", "secondary", "residential", "lane", "footway"}
KINDS = {"road", "park", "water", "rail", "campus", "building", "landmark", "place"}
CLAT, CLNG = 28.5933, 77.2507
KX = 111320 * math.cos(math.radians(CLAT))


@pytest.fixture(scope="module")
def city():
    return json.loads(CITY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def zone():
    return json.loads(ZONE.read_text(encoding="utf-8"))


def _metres(lng, lat):
    return ((lng - CLNG) * KX, (lat - CLAT) * 111320)


def _pts(f):
    g = f["geometry"]
    if g["type"] == "Point":
        return [g["coordinates"]]
    if g["type"] == "LineString":
        return g["coordinates"]
    return [c for ring in g["coordinates"] for c in ring]


# ------------------------------------------------------------- the file --
def test_city_file_exists_and_is_honest(city):
    assert city["type"] == "FeatureCollection"
    note = city["note"].lower()
    # The map's attribution says "representative, not surveyed"; the file
    # itself must never claim otherwise.
    assert "not surveyed" in note
    assert "invented" in note
    assert city["features"]


def test_city_stays_small_enough_to_ship_on_every_page_load():
    assert CITY.stat().st_size < 1_500_000, "demo_city.geojson is getting heavy"


def test_city_schema_matches_the_zone(city):
    for f in city["features"]:
        p = f["properties"]
        assert p["kind"] in KINDS, p
        if p["kind"] == "road":
            assert p["class"] in ROAD_CLASSES, p
            assert f["geometry"]["type"] == "LineString"
            assert len(f["geometry"]["coordinates"]) >= 2
        if p["kind"] == "place":
            assert p["rank"] in (1, 2)
            assert p["name"]


def test_city_covers_every_direction_out_to_the_camera_clamp(city):
    """app.js clamps the camera to +/-10 km; there must be geometry in all
    four quadrants out near that edge, or panning still finds a void."""
    far = {}
    for f in city["features"]:
        if f["properties"]["kind"] != "road":
            continue
        for lng, lat in f["geometry"]["coordinates"]:
            x, y = _metres(lng, lat)
            q = (x >= 0, y >= 0)
            far[q] = max(far.get(q, 0), min(abs(x), abs(y)))
    assert len(far) == 4, "a quadrant has no roads at all"
    for q, reach in far.items():
        assert reach > 7000, f"quadrant {q} only reaches {reach:.0f} m"


def test_city_never_overdraws_the_pilot_zone(city, zone):
    """Generated streets must keep clear of the hand-built network: the zone
    is the real map, the city is scenery around it."""
    zone_pts = []
    for f in zone["features"]:
        if f["properties"]["kind"] == "road":
            zone_pts += [_metres(*c) for c in f["geometry"]["coordinates"]]
    # coarse spatial index at 100 m so this stays fast
    grid = {}
    for x, y in zone_pts:
        grid.setdefault((int(x // 100), int(y // 100)), []).append((x, y))

    def nearest(px, py):
        gi, gj = int(px // 100), int(py // 100)
        best = 1e9
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for qx, qy in grid.get((gi + di, gj + dj), ()):
                    best = min(best, math.hypot(px - qx, py - qy))
        return best

    worst = 1e9
    for f in city["features"]:
        if f["properties"]["kind"] != "road":
            continue
        co = f["geometry"]["coordinates"]
        # endpoints are deliberately SNAPPED onto zone junctions (that is the
        # seam join) — the interior of a city road is what must stay clear
        for lng, lat in co[1:-1]:
            worst = min(worst, nearest(*_metres(lng, lat)))
    assert worst > 60, f"city street runs {worst:.0f} m from a pilot-zone road"


def test_city_is_not_routable(city):
    """The router reads demo_zone.geojson only. If that ever changes, a
    rider could be dispatched down an invented street — so no routable node
    may sit beyond the hand-built zone's own extent, while the city reaches
    10 km out."""
    n_city = sum(1 for f in city["features"] if f["properties"]["kind"] == "road")
    assert n_city > 100                       # the city really does have streets

    graph = routing.RoadGraph()
    assert graph.nodes
    worst = max(math.hypot(*_metres(lng, lat)) for lat, lng in graph.nodes)
    assert worst < 2500, (
        f"the road graph reaches {worst:.0f} m — it has swallowed city scenery")

    city_reach = max(
        math.hypot(*_metres(lng, lat))
        for f in city["features"] if f["properties"]["kind"] == "road"
        for lng, lat in f["geometry"]["coordinates"])
    assert city_reach > 8000


def test_generator_is_deterministic(tmp_path):
    """Re-running the tool must reproduce the committed file byte-for-byte,
    so a regenerate never shows up as a mystery diff."""
    import importlib.util
    tools = Path(__file__).resolve().parents[1] / "tools"
    spec = importlib.util.spec_from_file_location(
        "make_city_surrounds", tools / "make_city_surrounds.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fc = mod.build()
    assert json.dumps(fc, separators=(",", ":")) == CITY.read_text(encoding="utf-8")


# ------------------------------------------------------------- basemap --
def test_basemap_renders_both_sources_and_places():
    text = (STATIC / "basemap.js").read_text(encoding="utf-8")
    assert "cityUrl" in text
    assert "terrainLayers" in text          # one styling path for both sources
    assert '"place-district"' in text or "place-district" in text


def test_pages_ask_for_the_city():
    for name in ("app.js", "witness.js"):
        text = (STATIC / name).read_text(encoding="utf-8")
        assert "/data/demo_city.geojson" in text, name
        assert "CITY_HALF_M" in text, name


def test_city_is_served(tmp_path):
    from fastapi.testclient import TestClient

    from pukaar.api import build_app
    cfg = Config()
    cfg.backend = "mock"
    client = TestClient(build_app(cfg))
    r = client.get("/data/demo_city.geojson")
    assert r.status_code == 200
    assert r.json()["type"] == "FeatureCollection"


# -------------------------------------------------------- smooth motion --
def _mk(ambient=False, seed=42):
    cfg = Config()
    cfg.backend = "mock"
    cfg.sim_ambient = ambient
    holder = {}
    svc = PukaarService(cfg, Store(":memory:"), now_fn=lambda: holder["sim"].sim_now)
    sim = Sim(svc, cfg, seed=seed)
    holder["sim"] = sim
    return cfg, svc, sim


def test_speed_mps_is_the_speed_the_sim_actually_moves_by():
    """The map advances each rider by speed_mps x sim speed between polls.
    If this drifts from _responders_move, the dot stalls or overshoots and
    snaps back once a second — the exact bug the glide rewrite removed."""
    _cfg, _svc, sim = _mk(ambient=True)
    for _ in range(120):
        sim.tick(1.0)
    views = sim.snapshot()["responders"]
    assert views
    for v in views:
        assert "speed_mps" in v
        assert v["speed_mps"] >= 0
        if v["state"] == "enroute":
            assert v["speed_mps"] == pytest.approx(MODE_SPEED_MPS[v["mode"]])


def test_calm_idle_riders_report_zero_speed():
    """A calm-board rider standing still must report 0, not their mode
    speed: the map would otherwise dead-reckon them off down the road."""
    _cfg, _svc, sim = _mk(ambient=False)
    sim.tick(1.0)
    for v in sim.snapshot()["responders"]:
        if v["state"] == "idle":
            assert v["speed_mps"] == 0.0
