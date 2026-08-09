"""The demo-zone street network: schema contract, graph connectivity, and
the OSM importer in tools/.

The zone is REAL: pukaar/data/demo_zone.geojson is OpenStreetMap's survey
of Nizamuddin, Delhi, imported by tools/fetch_real_roads.py. That changes
what these tests can assert. A hand-built map could be held to tidy
invariants (every building set back from every kerb, exactly two rail
crossings) because a generator put it there. A real city obeys no such
rules — buildings sit hard against the street, flyovers cross the railway
wherever the engineers put them.

So what is pinned here is what the ROUTER depends on and what the map
promises: roads connect where they share a vertex, the whole network is
one walkable component and one scooter-able component (footways
excluded), nothing routable is a railway, and the file still says plainly
where it came from.
"""

import importlib.util
import json
import math
from pathlib import Path

import pytest

from pukaar import geo

ZONE_LAT, ZONE_LNG = 28.5933, 77.2507
DATA = Path(__file__).resolve().parents[1] / "pukaar" / "data" / "demo_zone.geojson"
TOOLS = Path(__file__).resolve().parents[1] / "tools"

ROAD_CLASSES = {"primary", "secondary", "residential", "lane", "footway"}
AREA_KINDS = {"park", "water", "campus"}
ICONS = {"rail", "monument", "mosque", "park", "hospital", "market"}


def _load_tool(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def fetch():
    return _load_tool("fetch_real_roads")


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
def test_the_file_says_where_it_came_from(fc):
    """ODbL requires attribution, and the demo's whole credibility rests on
    this map being the real one — so the provenance travels IN the file."""
    assert fc["type"] == "FeatureCollection"
    assert "OpenStreetMap" in fc["note"]
    assert "OpenStreetMap contributors" in fc["attribution"]
    assert "ODbL" in fc["license"]
    src = fc["source"]
    assert src["profile"] == "zone"
    assert src["center"] == [ZONE_LNG, ZONE_LAT]


def test_the_map_is_light_enough_to_ship_on_every_page_load():
    """Real streets cost bytes, and the control room fetches this on every
    cold load. What matters is the wire size: the app gzips responses
    (GZipMiddleware in api.py), and GeoJSON compresses ~8x."""
    import gzip
    raw = DATA.read_bytes()
    assert len(raw) < 950_000
    assert len(gzip.compress(raw, 6)) < 200_000


def test_every_feature_matches_the_contract(fc):
    for f in fc["features"]:
        props, g = f["properties"], f["geometry"]
        kind = props["kind"]
        if kind == "road":
            assert props["class"] in ROAD_CLASSES
            assert g["type"] == "LineString" and len(g["coordinates"]) >= 2
        elif kind == "rail":
            # OSM maps tracks as centrelines and railway land as polygons;
            # the basemap draws both, so both are legal here.
            assert g["type"] in ("LineString", "Polygon")
        elif kind in AREA_KINDS:
            assert g["type"] == "Polygon"
            ring = g["coordinates"][0]
            assert len(ring) >= 4 and ring[0] == ring[-1]
        elif kind == "building":
            assert g["type"] == "Polygon"
            ring = g["coordinates"][0]
            # a real footprint is any closed ring, not the generator's quad
            assert len(ring) >= 4 and ring[0] == ring[-1]
        elif kind == "landmark":
            assert g["type"] == "Point"
            assert props["icon"] in ICONS and props["name"]
        else:
            raise AssertionError(f"unknown kind {kind!r}")


def test_road_count_and_real_street_names(fc):
    roads = _roads(fc)
    assert 800 <= len(roads) <= 3000
    names = {f["properties"].get("name") for f in roads} - {None}
    assert len(names) >= 40
    # The two arterials the pilot zone is framed by, exactly as OSM names
    # them. If an import ever loses these, it fetched the wrong place.
    assert {"Mathura Road", "Lodhi Road"} <= names


def _buildings(fc):
    return [f for f in fc["features"] if f["properties"]["kind"] == "building"]


def test_building_footprints_are_present(fc):
    """Nizamuddin is dense; the footprints are what make the map read as a
    real neighbourhood rather than a street diagram."""
    assert 800 <= len(_buildings(fc)) <= 4000


def test_landmarks_are_the_real_ones(fc):
    lms = [f for f in fc["features"] if f["properties"]["kind"] == "landmark"]
    assert len(lms) >= 20
    names = {f["properties"]["name"] for f in lms}
    # OSM maps three of these four as AREAS, not nodes — they only appear
    # because the importer labels named areas at their centroid.
    assert {"Humayun's Tomb", "Sunder Nursery", "Nizamuddin Dargah",
            "Hazrat Nizamuddin Junction"} <= names
    assert len(names) == len(lms), "one label per place"


def test_everything_within_the_demo_zone(fc):
    """Roads are clipped to a 1600 m disc; areas are kept whole when their
    centre is inside it, so a park may overhang a little."""
    for f in fc["features"]:
        g = f["geometry"]
        pts = ([g["coordinates"]] if g["type"] == "Point"
               else g["coordinates"] if g["type"] == "LineString"
               else g["coordinates"][0])
        for lng, lat in pts:
            assert geo.haversine_m(ZONE_LAT, ZONE_LNG, lat, lng) <= 2100


# -------------------------------------------------------------- graph --
def test_no_degenerate_edges(fc):
    """Sub-metre edges are survey noise (two nodes at one junction), not
    geometry — the importer welds them, so none may survive."""
    for f in _roads(fc):
        cs = f["geometry"]["coordinates"]
        for a, b in zip(cs, cs[1:]):
            assert _vertex(a) != _vertex(b), f["properties"]
            assert geo.haversine_m(a[1], a[0], b[1], b[0]) > 1.0


def test_all_roads_are_one_component(fc):
    assert _component_count(_roads(fc)) == 1


def test_scooter_subgraph_is_one_component(fc):
    scooter = [f for f in _roads(fc) if f["properties"]["class"] != "footway"]
    assert len(scooter) >= 300          # footways are texture, not the mesh
    assert _component_count(scooter) == 1


def test_railways_are_drawn_but_never_routable(fc):
    """The one rail invariant that still means something on a real map: a
    rider is never sent down a track. Rail is not a road class, so it can
    never enter the graph — assert that end to end, on the real router."""
    from pukaar import routing

    rails = [f for f in fc["features"] if f["properties"]["kind"] == "rail"]
    assert rails, "Nizamuddin is a railway junction; the tracks belong here"

    rail_vertices = {_vertex(c) for f in rails
                     for c in (f["geometry"]["coordinates"]
                               if f["geometry"]["type"] == "LineString"
                               else f["geometry"]["coordinates"][0])}
    graph = routing.RoadGraph(DATA)
    assert rail_vertices, "rail geometry has no vertices"
    assert not (rail_vertices & set(graph.nodes)), \
        "a railway vertex became a routable node"


# ------------------------------------------------------- OSM importer --
def test_osm_tag_to_class_mapping(fetch):
    assert fetch.road_class({"highway": "primary"}) == "primary"
    assert fetch.road_class({"highway": "trunk_link"}) == "primary"
    assert fetch.road_class({"highway": "tertiary"}) == "secondary"
    assert fetch.road_class({"highway": "residential"}) == "residential"
    assert fetch.road_class({"highway": "service"}) == "lane"
    assert fetch.road_class({"highway": "steps"}) == "footway"
    assert fetch.road_class({"waterway": "drain"}) is None
    assert fetch.road_class(None) is None
    # a street that is not open is not a street
    assert fetch.road_class({"highway": "construction"}) is None
    assert fetch.road_class({"highway": "proposed"}) is None


def test_osm_area_and_landmark_mapping(fetch):
    assert fetch.area_kind({"leisure": "park"}) == "park"
    assert fetch.area_kind({"natural": "water"}) == "water"
    assert fetch.area_kind({"landuse": "railway"}) == "rail"
    assert fetch.area_kind({"highway": "primary"}) is None
    assert fetch.landmark_icon({"railway": "station"}) == "rail"
    assert fetch.landmark_icon({"amenity": "place_of_worship",
                                "religion": "muslim"}) == "mosque"
    assert fetch.landmark_icon({"amenity": "cafe"}) is None
    # a dargah carries both tags and is a mosque first
    assert fetch.landmark_icon({"amenity": "place_of_worship",
                                "religion": "muslim",
                                "historic": "monument"}) == "mosque"
    assert fetch.landmark_icon({"historic": "monument"}) == "monument"
    assert fetch.place_rank({"place": "suburb"}) == 1
    assert fetch.place_rank({"place": "neighbourhood"}) == 2
    assert fetch.place_rank({"place": "farm"}) is None


def test_region_zone_is_a_disc_and_city_is_the_clamp_square(fetch):
    """The city tier fills the square the camera can pan to, not a disc —
    a disc leaves the corners of that square empty."""
    zone = fetch.region("zone", ZONE_LAT, ZONE_LNG, 0.0, 1600.0)
    city = fetch.region("city", ZONE_LAT, ZONE_LNG, 1600.0, 10_000.0)

    def at(east_m, north_m):
        return [ZONE_LNG + east_m / (111_320 * math.cos(math.radians(ZONE_LAT))),
                ZONE_LAT + north_m / 111_320]

    assert zone(at(0, 0)) and zone(at(0, 1500))
    assert not zone(at(0, 1700))
    # the zone hole: the city tier must not overdraw the pilot area
    assert not city(at(0, 0)) and not city(at(0, 1500))
    assert city(at(0, 2000))
    # the corner of the clamp square is 14.1 km out and must still be in
    assert city(at(9900, 9900))
    assert not city(at(10_500, 0))


def test_clip_line_interpolates_the_boundary(fetch):
    """A clipped street ends ON the boundary, not at whichever vertex
    happened to be the last one inside."""
    inside = fetch.region("zone", ZONE_LAT, ZONE_LNG, 0.0, 1000.0)
    north = 1.0 / 111_320
    line = [[ZONE_LNG, ZONE_LAT + n * 500 * north] for n in range(6)]  # 0..2500 m
    parts = fetch.clip_line(line, inside)
    assert len(parts) == 1
    end = parts[0][-1]
    assert geo.haversine_m(ZONE_LAT, ZONE_LNG, end[1], end[0]) == pytest.approx(1000, abs=1)


def test_clip_line_can_split_one_way_into_two(fetch):
    """A road that leaves the region and comes back is two roads, not one
    with a phantom shortcut across the gap."""
    inside = fetch.region("city", ZONE_LAT, ZONE_LNG, 1600.0, 10_000.0)
    north = 1.0 / 111_320
    line = [[ZONE_LNG, ZONE_LAT + m * north] for m in (-5000, -2000, 0, 2000, 5000)]
    parts = fetch.clip_line(line, inside)
    assert len(parts) == 2


def test_merge_close_nodes_welds_a_survey_gap(fetch):
    """Two nodes 30 cm apart are one junction. Welded, the crossing is
    real; left alone, the router sees two dead ends."""
    d = 0.3 / 111_320
    roads = [
        {"properties": {"kind": "road", "class": "residential"},
         "geometry": {"type": "LineString",
                      "coordinates": [[77.0, 28.0], [77.0, 28.001]]}},
        {"properties": {"kind": "road", "class": "residential"},
         "geometry": {"type": "LineString",
                      "coordinates": [[77.0, 28.001 + d], [77.001, 28.001]]}},
    ]
    out = fetch.merge_close_nodes(roads, tol_m=1.2)
    assert len(out) == 2
    joined = out[0]["geometry"]["coordinates"][-1]
    assert joined == out[1]["geometry"]["coordinates"][0]


def test_merge_close_nodes_drops_a_collapsed_way(fetch):
    """A way whose every node welds into one point is not a road."""
    d = 0.2 / 111_320
    roads = [{"properties": {"kind": "road", "class": "lane"},
              "geometry": {"type": "LineString",
                           "coordinates": [[77.0, 28.0], [77.0, 28.0 + d]]}}]
    assert fetch.merge_close_nodes(roads, tol_m=1.2) == []


def test_thin_roads_keeps_junctions(fetch):
    """Thinning drops redundant detail but must never drop a shared vertex
    — that would silently disconnect the network."""
    step = 0.4 / 111_320                      # 40 cm apart: below the gap
    a = {"properties": {"kind": "road", "class": "residential"},
         "geometry": {"type": "LineString",
                      "coordinates": [[77.0, 28.0 + i * step] for i in range(6)]}}
    junction = [77.0, 28.0 + 3 * step]
    b = {"properties": {"kind": "road", "class": "residential"},
         "geometry": {"type": "LineString",
                      "coordinates": [junction, [77.001, 28.001]]}}
    fetch.thin_roads([a, b], min_gap_m=1.5)
    assert junction in a["geometry"]["coordinates"], "junction was thinned away"
    assert len(a["geometry"]["coordinates"]) < 6, "nothing was thinned"


def test_prune_keeps_the_mesh_and_drops_islands(fetch):
    """An orphan block would be answered with a straight line — a rider
    'flying' over the city. It must not survive the import."""
    def road(cls, pts):
        return {"properties": {"kind": "road", "class": cls},
                "geometry": {"type": "LineString", "coordinates": pts}}

    mesh = [road("residential", [[77.0, 28.0], [77.001, 28.0]]),
            road("residential", [[77.001, 28.0], [77.002, 28.0]])]
    island = road("residential", [[77.5, 28.5], [77.501, 28.5]])
    attached_foot = road("footway", [[77.001, 28.0], [77.001, 28.001]])
    orphan_foot = road("footway", [[77.9, 28.9], [77.901, 28.9]])

    kept = fetch.prune_to_one_component(mesh + [island, attached_foot, orphan_foot])
    coords = [f["geometry"]["coordinates"] for f in kept]
    assert island["geometry"]["coordinates"] not in coords
    assert orphan_foot["geometry"]["coordinates"] not in coords
    assert attached_foot["geometry"]["coordinates"] in coords
    assert len(kept) == 3


def test_simplify_drops_collinear_detail_but_keeps_corners(fetch):
    straight = [[77.0, 28.0], [77.0005, 28.0], [77.001, 28.0]]
    assert len(fetch.simplify(straight, 5.0, 28.0, 77.0)) == 2

    corner = [[77.0, 28.0], [77.0005, 28.0005], [77.001, 28.0]]
    assert len(fetch.simplify(corner, 5.0, 28.0, 77.0)) == 3
