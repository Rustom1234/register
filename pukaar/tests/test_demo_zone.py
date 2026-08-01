"""The demo-zone street network: schema contract, graph connectivity,
rail-crossing discipline, and the deterministic generator + OSM importer
in tools/. Roads connect where they share an exact 6-decimal-place vertex;
the whole network must be one walkable component and one scooter-able
component (footways excluded)."""

import importlib.util
import json
import math
import random
from pathlib import Path

import pytest

from pukaar import geo

ZONE_LAT, ZONE_LNG = 28.5933, 77.2507
DATA = Path(__file__).resolve().parents[1] / "pukaar" / "data" / "demo_zone.geojson"
TOOLS = Path(__file__).resolve().parents[1] / "tools"

ROAD_CLASSES = {"primary", "secondary", "residential", "lane", "footway"}
AREA_KINDS = {"park", "water", "rail", "campus"}
ICONS = {"rail", "monument", "mosque", "park", "hospital", "market"}


def _load_tool(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def fc():
    return json.loads(DATA.read_text(encoding="utf-8"))


def _roads(fc):
    return [f for f in fc["features"] if f["properties"]["kind"] == "road"]


def _vertex(pt):
    return (round(pt[0], 6), round(pt[1], 6))


def _component_count(roads):
    adj = {}
    for f in roads:
        cs = f["geometry"]["coordinates"]
        for a, b in zip(cs, cs[1:]):
            ka, kb = _vertex(a), _vertex(b)
            adj.setdefault(ka, set()).add(kb)
            adj.setdefault(kb, set()).add(ka)
    seen, comps = set(), 0
    for start in adj:
        if start in seen:
            continue
        comps += 1
        stack = [start]
        seen.add(start)
        while stack:
            for n in adj[stack.pop()]:
                if n not in seen:
                    seen.add(n)
                    stack.append(n)
    return comps


# ------------------------------------------------------------- schema --
def test_parses_with_note_and_size(fc):
    assert fc["type"] == "FeatureCollection"
    assert "NOT surveyed" in fc["note"]
    assert DATA.stat().st_size < 700_000


def test_every_feature_matches_the_contract(fc):
    for f in fc["features"]:
        props, g = f["properties"], f["geometry"]
        kind = props["kind"]
        if kind == "road":
            assert props["class"] in ROAD_CLASSES
            assert g["type"] == "LineString" and len(g["coordinates"]) >= 2
        elif kind in AREA_KINDS:
            assert g["type"] == "Polygon"
            ring = g["coordinates"][0]
            assert len(ring) >= 4 and ring[0] == ring[-1]
        elif kind == "building":
            assert g["type"] == "Polygon"
            ring = g["coordinates"][0]
            assert len(ring) == 5 and ring[0] == ring[-1]  # closed quad
        elif kind == "landmark":
            assert g["type"] == "Point"
            assert props["icon"] in ICONS and props["name"]
        else:
            raise AssertionError(f"unknown kind {kind!r}")


def test_road_count_and_names(fc):
    roads = _roads(fc)
    assert 150 <= len(roads) <= 350
    names = {f["properties"].get("name") for f in roads} - {None}
    assert len(names) >= 8
    assert {"Mathura Road", "Lodhi Road"} <= names


def _buildings(fc):
    return [f for f in fc["features"] if f["properties"]["kind"] == "building"]


def _to_m(pt):
    """[lng, lat] -> local metres east/north of the zone center — the
    inverse of the generator's geo.offset_m(ZONE_LAT, ZONE_LNG, ...)."""
    lng, lat = pt
    return ((lng - ZONE_LNG) * 111_320.0 * math.cos(math.radians(ZONE_LAT)),
            (lat - ZONE_LAT) * 111_320.0)


def _seg_dist_m(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def test_building_count_range(fc):
    assert 250 <= len(_buildings(fc)) <= 500


def test_sampled_buildings_keep_clear_of_road_centerlines(fc):
    """No building vertex within 3.5 m of any road centerline segment,
    spot-checked on ~40 seeded-random buildings against every road."""
    segs = []
    for road in _roads(fc):
        cs = [_to_m(c) for c in road["geometry"]["coordinates"]]
        segs.extend(zip(cs, cs[1:]))
    sample = random.Random(42).sample(_buildings(fc), 40)
    for f in sample:
        for pt in f["geometry"]["coordinates"][0][:-1]:
            p = _to_m(pt)
            d = min(_seg_dist_m(p, a, b) for a, b in segs)
            assert d >= 3.5, (f["geometry"]["coordinates"][0], d)


def test_landmarks(fc):
    lms = [f for f in fc["features"] if f["properties"]["kind"] == "landmark"]
    assert len(lms) >= 5
    names = {f["properties"]["name"] for f in lms}
    assert {"Hazrat Nizamuddin Railway Station", "Hazrat Nizamuddin Dargah",
            "Humayun's Tomb", "Sunder Nursery"} <= names


def test_everything_within_the_demo_zone(fc):
    for f in fc["features"]:
        g = f["geometry"]
        pts = ([g["coordinates"]] if g["type"] == "Point"
               else g["coordinates"] if g["type"] == "LineString"
               else g["coordinates"][0])
        for lng, lat in pts:
            assert geo.haversine_m(ZONE_LAT, ZONE_LNG, lat, lng) <= 2100


# -------------------------------------------------------------- graph --
def test_no_degenerate_edges(fc):
    for f in _roads(fc):
        cs = f["geometry"]["coordinates"]
        for a, b in zip(cs, cs[1:]):
            assert _vertex(a) != _vertex(b), f["properties"]
            assert geo.haversine_m(a[1], a[0], b[1], b[0]) > 1.0


def test_all_roads_are_one_component(fc):
    assert _component_count(_roads(fc)) == 1


def test_scooter_subgraph_is_one_component(fc):
    scooter = [f for f in _roads(fc) if f["properties"]["class"] != "footway"]
    assert len(scooter) >= 100          # footways are texture, not the mesh
    assert _component_count(scooter) == 1


# ------------------------------------------------------- rail crossing --
def _segments_cross(p, q, r, s):
    def d(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return (d(r, s, p) * d(r, s, q) < 0) and (d(p, q, r) * d(p, q, s) < 0)


def test_roads_cross_the_rail_band_only_at_designated_points(fc):
    rails = [f for f in fc["features"] if f["properties"]["kind"] == "rail"]
    assert rails, "the corridor polygon is part of the demo"
    hits = 0
    for rail in rails:
        ring = rail["geometry"]["coordinates"][0]
        for e1, e2 in zip(ring, ring[1:]):
            for road in _roads(fc):
                cs = road["geometry"]["coordinates"]
                hits += sum(_segments_cross(a, b, e1, e2)
                            for a, b in zip(cs, cs[1:]))
    # 2 designated crossings x 2 band edges each = 4; a little slack only
    assert 2 <= hits <= 6, hits


# ----------------------------------------------------------- generator --
def test_generator_reproduces_the_committed_file(tmp_path):
    gen = _load_tool("make_demo_zone")
    fc2 = gen.generate()
    assert fc2 == json.loads(DATA.read_text(encoding="utf-8"))
    assert gen.render(fc2) == DATA.read_text(encoding="utf-8")


def test_generator_is_deterministic():
    gen = _load_tool("make_demo_zone")
    assert gen.render(gen.generate()) == gen.render(gen.generate())


# ------------------------------------------------------- OSM importer --
def test_osm_tag_to_class_mapping():
    fetch = _load_tool("fetch_real_roads")
    assert fetch.road_class({"highway": "primary"}) == "primary"
    assert fetch.road_class({"highway": "trunk_link"}) == "primary"
    assert fetch.road_class({"highway": "tertiary"}) == "secondary"
    assert fetch.road_class({"highway": "residential"}) == "residential"
    assert fetch.road_class({"highway": "service"}) == "lane"
    assert fetch.road_class({"highway": "steps"}) == "footway"
    assert fetch.road_class({"waterway": "drain"}) is None
    assert fetch.road_class(None) is None


def test_osm_area_and_landmark_mapping():
    fetch = _load_tool("fetch_real_roads")
    assert fetch.area_kind({"leisure": "park"}) == "park"
    assert fetch.area_kind({"natural": "water"}) == "water"
    assert fetch.area_kind({"landuse": "railway"}) == "rail"
    assert fetch.area_kind({"highway": "primary"}) is None
    assert fetch.landmark_icon({"railway": "station"}) == "rail"
    assert fetch.landmark_icon({"amenity": "place_of_worship",
                                "religion": "muslim"}) == "mosque"
    assert fetch.landmark_icon({"amenity": "cafe"}) is None
