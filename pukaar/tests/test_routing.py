"""Routing engine v2: GeoJSON road graph, travel modes, A*, edge snapping.

All tests run against the hand-written mini fixture (a primary ring with a
diagonal footway shortcut across it) so they don't depend on the real
demo_zone.geojson being present. Node letters used in comments:

    D(28.594,77.250) ---- C(28.594,77.254)      primary ring: A-B-F-C-D-E-A
    |              \\          |                 footway:      A-M-C (diagonal)
    E --- M --- F  (28.592 row, residential)    spurs: B-G secondary, D-H lane
    |         /               |
    A(28.590,77.250) ---- B(28.590,77.254)
"""

from pathlib import Path

import pytest

from pukaar import geo
from pukaar.routing import RoadGraph, SPEEDS_KMH, route_remaining_m

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mini_zone.geojson"

A = (28.590, 77.250)
B = (28.590, 77.254)
F = (28.592, 77.254)
C = (28.594, 77.254)
D = (28.594, 77.250)
E = (28.592, 77.250)
M = (28.592, 77.252)   # footway/residential crossing mid-ring


@pytest.fixture(scope="module")
def graph() -> RoadGraph:
    return RoadGraph(FIXTURE)


def _has_point(waypoints, pt, tol=1e-7) -> bool:
    return any(abs(w[0] - pt[0]) < tol and abs(w[1] - pt[1]) < tol for w in waypoints)


# ---------------------------------------------------------------- loading --

def test_loads_mini_fixture(graph):
    # 9 road vertices; the park polygon and landmark point are map
    # dressing and must NOT become graph nodes.
    assert len(graph.nodes) == 9
    assert len(graph.edges) == 12
    assert (28.5905, 77.2505) not in graph.nodes   # park corner
    assert (28.594, 77.256) not in graph.nodes     # landmark
    for pt in (A, B, C, D, E, F, M):
        assert pt in graph.nodes


def test_missing_path_raises_clearly():
    bogus = "/no/such/dir/zone.geojson"
    with pytest.raises(FileNotFoundError) as exc:
        RoadGraph(bogus)
    assert bogus in str(exc.value)
    assert "demo_zone.geojson" in str(exc.value)


def test_unknown_mode_rejected(graph):
    with pytest.raises(ValueError):
        graph.route(*A, *C, mode="helicopter")


# ------------------------------------------------------------ mode logic --

def test_walk_takes_footway_scooter_detours(graph):
    walk_wp, walk_m, walk_s = graph.route(*A, *C, mode="walk")
    scoot_wp, scoot_m, scoot_s = graph.route(*A, *C, mode="scooter")

    # Walk cuts the diagonal footway through M; the scooter is forbidden
    # there and must go around the ring.
    assert _has_point(walk_wp, M)
    assert not _has_point(scoot_wp, M)

    # Detour is longer in metres but far quicker at 28 km/h vs 5 km/h.
    assert scoot_m > walk_m
    assert scoot_s < walk_s

    # Hand check: walk = A-M-C diagonal; scooter rounds the ring's west
    # side A-E-D-C (a hair shorter than A-B-F-C: the top east-west edge
    # sits at higher latitude, so its metres-per-degree are smaller).
    diag = geo.haversine_m(*A, *M) + geo.haversine_m(*M, *C)
    ring = geo.haversine_m(*A, *E) + geo.haversine_m(*E, *D) + geo.haversine_m(*D, *C)
    assert walk_m == pytest.approx(diag, rel=1e-9)
    assert scoot_m == pytest.approx(ring, rel=1e-9)
    assert walk_s == pytest.approx(diag / (5.0 / 3.6), rel=1e-9)
    assert scoot_s == pytest.approx(ring / (28.0 / 3.6), rel=1e-9)


def test_duration_is_sum_of_edge_times_two_edge_route(graph):
    # Cycle E->F: fastest is the residential cross-street E-M-F
    # (12 km/h) — exactly two edges, hand-checkable.
    wp, dist_m, dur_s = graph.route(*E, *F, mode="cycle")
    em = geo.haversine_m(*E, *M)
    mf = geo.haversine_m(*M, *F)
    assert dist_m == pytest.approx(em + mf, rel=1e-9)
    assert dur_s == pytest.approx((em + mf) / (12.0 / 3.6), rel=1e-9)
    assert _has_point(wp, M)


def test_speed_table_shape():
    # The contract with the sim: footway exists for walk/cycle, not scooter.
    assert "footway" in SPEEDS_KMH["walk"]
    assert "footway" in SPEEDS_KMH["cycle"]
    assert "footway" not in SPEEDS_KMH["scooter"]


# -------------------------------------------------------------- endpoints --

def test_waypoints_start_and_end_exactly_at_query_points(graph):
    start = (28.59031, 77.25077)   # deliberately off every vertex
    end = (28.59377, 77.25322)
    for mode in ("walk", "cycle", "scooter"):
        wp, dist_m, dur_s = graph.route(*start, *end, mode=mode)
        assert wp[0] == start
        assert wp[-1] == end
        assert dist_m > 0 and dur_s > 0


def test_snaps_mid_block_not_to_intersection(graph):
    # Start just south of the middle of the A-B edge, end just north of
    # the middle of the D-C edge: entry/exit points must be mid-block
    # projections onto those edges, not either intersection.
    start = (28.58985, 77.2515)
    end = (28.59415, 77.2525)
    wp, dist_m, dur_s = graph.route(*start, *end, mode="scooter")

    entry, exit_ = wp[1], wp[-2]
    assert entry[0] == pytest.approx(28.590, abs=1e-9)      # on the A-B edge line
    assert entry[1] == pytest.approx(77.2515, abs=1e-7)     # straight across from start
    assert 77.250 < entry[1] < 77.254                       # strictly between vertices
    assert exit_[0] == pytest.approx(28.594, abs=1e-9)
    assert exit_[1] == pytest.approx(77.2525, abs=1e-7)
    assert 77.250 < exit_[1] < 77.254

    # Total includes the two short off-road approach legs.
    approach = geo.haversine_m(*start, *entry) + geo.haversine_m(*end, *exit_)
    assert approach == pytest.approx(dist_m - _polyline_m(wp[1:-1]), abs=0.5)


def _polyline_m(points) -> float:
    return sum(geo.haversine_m(*a, *b) for a, b in zip(points, points[1:]))


def test_walk_snap_prefers_nearby_footway(graph):
    # A point right next to the middle of the A-M footway leg: walkers
    # snap onto the footway; scooters must snap to a real road instead.
    near_diag = (28.5910, 77.2510)
    walk_wp, _, _ = graph.route(*near_diag, *C, mode="walk")
    assert _has_point(walk_wp, M)                            # entered via the footway
    scoot_wp, _, _ = graph.route(*near_diag, *C, mode="scooter")
    assert not _has_point(scoot_wp, M)


# --------------------------------------------------------- remaining dist --

def test_route_remaining_m_decreases_along_route(graph):
    wp, dist_m, _ = graph.route(*A, *C, mode="walk")
    # Standing at the start with everything ahead == full route length.
    assert route_remaining_m(wp, 0, *wp[0]) == pytest.approx(dist_m, abs=0.5)
    # Advancing to each waypoint monotonically shrinks what's left.
    rems = [route_remaining_m(wp, i, *wp[i]) for i in range(len(wp))]
    assert all(a > b for a, b in zip(rems, rems[1:]))
    assert rems[-1] == pytest.approx(0.0, abs=1e-6)
    # Mid-segment: halfway between wp[0] and wp[1], heading for wp[1].
    mid = ((wp[0][0] + wp[1][0]) / 2, (wp[0][1] + wp[1][1]) / 2)
    assert rems[1] < route_remaining_m(wp, 1, *mid) < rems[0]


# ----------------------------------------------------------- determinism --

def test_route_is_deterministic(graph):
    q = (28.59012, 77.25543, 28.59388, 77.24951)
    first = graph.route(*q, mode="cycle")
    for _ in range(3):
        assert graph.route(*q, mode="cycle") == first


# --------------------------------------------------------- snap index --
def test_snap_index_agrees_with_scanning_every_edge(graph):
    """Snapping is answered from a grid index (RoadGraph._index) so that a
    real OSM zone's ~7.6k edges are not rescanned twice per route. The
    index is an optimisation ONLY: it must return exactly what the linear
    scan returns, including for points off the edge of the map — a rider
    outside the zone must still snap to the nearest street rather than
    fall through to straight-line routing."""
    import random

    rng = random.Random(11)
    box = (min(n[0] for n in graph.nodes), max(n[0] for n in graph.nodes),
           min(n[1] for n in graph.nodes), max(n[1] for n in graph.nodes))
    pts = [(rng.uniform(box[0], box[1]), rng.uniform(box[2], box[3]))
           for _ in range(120)]
    # and well outside it, in every direction
    span = max(box[1] - box[0], box[3] - box[2]) or 0.01
    pts += [(rng.uniform(box[0] - 40 * span, box[1] + 40 * span),
             rng.uniform(box[2] - 40 * span, box[3] + 40 * span))
            for _ in range(120)]

    for mode, speeds in SPEEDS_KMH.items():
        for lat, lng in pts:
            fast = graph._snap(lat, lng, speeds)
            slow = graph._snap_into(lat, lng, speeds, range(len(graph.edges)), None)
            assert (fast is None) == (slow is None), (mode, lat, lng)
            if fast is not None:
                assert fast.approach_m == pytest.approx(slow.approach_m, abs=1e-9), \
                    (mode, lat, lng)
                assert fast.edge_i == slow.edge_i or \
                    fast.approach_m == pytest.approx(slow.approach_m, abs=1e-9)
