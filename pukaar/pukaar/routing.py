"""Offline routing over the demo zone's road graph.

v2: routes run over real road geometry loaded from a GeoJSON
FeatureCollection (pukaar/data/demo_zone.geojson — the surveyed streets of
Nizamuddin, Delhi, imported from OpenStreetMap by
tools/fetch_real_roads.py). Every consecutive coordinate pair of a road
LineString becomes an undirected edge carrying its haversine length and
road class; per-mode speeds (walk / cycle / scooter) turn lengths into
travel times, and A* finds the fastest path. Query points snap onto the
nearest legal *edge* — projected mid-block, not teleported to the nearest
intersection — so a rider halfway down a street starts halfway down that
street. Zero network calls, zero dependencies beyond the stdlib.

The old synthetic RoadMesh (deterministic rotated grid) is kept at the
bottom of this module as a fallback for environments without the GeoJSON
data file.
"""

from __future__ import annotations

import heapq
import json
import math
import random
from pathlib import Path

from . import geo

# Speeds in km/h by (mode, road class). A class missing from a mode's row
# is forbidden for that mode — the edge simply does not exist for it
# (scooters stay off footways).
SPEEDS_KMH: dict[str, dict[str, float]] = {
    "walk":    {"primary": 5.0, "secondary": 5.0, "residential": 5.0, "lane": 5.0, "footway": 5.0},
    "cycle":   {"primary": 15.0, "secondary": 14.0, "residential": 12.0, "lane": 10.0, "footway": 6.0},
    "scooter": {"primary": 28.0, "secondary": 22.0, "residential": 16.0, "lane": 10.0},
}

_APPROACH_KMH = 5.0   # door-to-road legs are always on foot (wheel the scooter over)
_M_PER_DEG_LAT = 111_320.0
_GRID_M = 120.0       # snap-index cell size; see RoadGraph._index

_DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "data" / "demo_zone.geojson"

# Sentinel node keys for the two per-query virtual nodes ("snapped start"
# and "snapped goal"). Real node keys are (lat, lng) float pairs, so a
# string never collides with one.
_START = "__start__"
_GOAL = "__goal__"


def _key(lat: float, lng: float) -> tuple[float, float]:
    """Graph node key: coordinates rounded to 6 dp (~11cm) so roads that
    share a vertex in the GeoJSON connect exactly."""
    return (round(lat, 6), round(lng, 6))


class _Snap:
    """Where a query point entered the graph: the projection onto its
    nearest mode-legal edge, plus the along-edge split distances."""

    __slots__ = ("edge_i", "lat", "lng", "a", "b", "dist_a", "dist_b", "cls", "approach_m")

    def __init__(self, edge_i, lat, lng, a, b, dist_a, dist_b, cls, approach_m):
        self.edge_i = edge_i
        self.lat, self.lng = lat, lng
        self.a, self.b = a, b
        self.dist_a, self.dist_b = dist_a, dist_b
        self.cls = cls
        self.approach_m = approach_m


class RoadGraph:
    """A routable street graph loaded from the demo-zone GeoJSON."""

    def __init__(self, path: str | Path | None = None):
        p = Path(path) if path is not None else _DEFAULT_DATA_PATH
        if not p.exists():
            raise FileNotFoundError(
                f"road graph data not found at {p} — generate "
                "pukaar/data/demo_zone.geojson (see tools/fetch_real_roads.py) "
                "or pass an explicit path to RoadGraph()."
            )
        data = json.loads(p.read_text(encoding="utf-8"))

        self.nodes: dict[tuple[float, float], tuple[float, float]] = {}
        # adjacency: node -> [(neighbor, length_m, road_class), ...]
        self.adj: dict[tuple[float, float], list[tuple[tuple[float, float], float, str]]] = {}
        # flat edge list for snapping: (a_key, b_key, length_m, road_class, name)
        self.edges: list[tuple[tuple[float, float], tuple[float, float], float, str, str]] = []
        # unordered node pair -> street name, for turn-by-turn reconstruction
        self._edge_name: dict[tuple[tuple[float, float], tuple[float, float]], str] = {}
        self._build(data)

    # ------------------------------------------------------------- build --
    def _build(self, data: dict) -> None:
        seen: set[tuple[tuple[float, float], tuple[float, float]]] = set()
        for feat in data.get("features", []):
            props = feat.get("properties", {})
            if props.get("kind") != "road":
                continue  # parks / water / landmarks are map dressing, not routable
            cls = props.get("class", "residential")
            name = props.get("name") or ""   # "" = unnamed gali / footway
            coords = feat.get("geometry", {}).get("coordinates", [])
            for (lng1, lat1), (lng2, lat2) in zip(coords, coords[1:]):
                a, b = _key(lat1, lng1), _key(lat2, lng2)
                if a == b:
                    continue
                pair = (min(a, b), max(a, b))
                if pair in seen:
                    continue  # same segment drawn twice — keep the first
                seen.add(pair)
                d = geo.haversine_m(a[0], a[1], b[0], b[1])
                for n in (a, b):
                    if n not in self.nodes:
                        self.nodes[n] = n
                        self.adj[n] = []
                self.adj[a].append((b, d, cls))
                self.adj[b].append((a, d, cls))
                self.edges.append((a, b, d, cls, name))
                self._edge_name[pair] = name
        self._index()

    # ------------------------------------------------------------- index --
    def _index(self) -> None:
        """Bucket every edge into a ~120 m grid so snapping is local.

        Real OSM streets make this necessary: the surveyed pilot zone has
        ~7.6k edges where the old hand-drawn one had a few hundred, and
        _snap runs twice per route while dispatch routes every candidate
        rider against every open case. A linear scan turned that into the
        dominant cost of the whole system (300-case ingest went from ~20 s
        to ~38 s); bucketing puts it back to a handful of cells."""
        self._classes = {e[3] for e in self.edges}
        self._grid: dict[tuple[int, int], list[int]] = {}
        if not self.edges:
            self._grid_bounds = (0, -1, 0, -1)
            self._m_lng = _M_PER_DEG_LAT
            return
        lat0 = sum(n[0] for n in self.nodes) / len(self.nodes)
        self._m_lng = _M_PER_DEG_LAT * max(0.2, math.cos(math.radians(lat0)))
        for i, (a, b, _len, _cls, _name) in enumerate(self.edges):
            (ai, aj), (bi, bj) = self._cell(*a), self._cell(*b)
            for gi in range(min(ai, bi), max(ai, bi) + 1):
                for gj in range(min(aj, bj), max(aj, bj) + 1):
                    self._grid.setdefault((gi, gj), []).append(i)
        gis = [c[0] for c in self._grid]
        gjs = [c[1] for c in self._grid]
        self._grid_bounds = (min(gis), max(gis), min(gjs), max(gjs))

    def _cell(self, lat: float, lng: float) -> tuple[int, int]:
        return (int(math.floor(lng * self._m_lng / _GRID_M)),
                int(math.floor(lat * _M_PER_DEG_LAT / _GRID_M)))

    @staticmethod
    def _ring(gi: int, gj: int, r: int):
        if r == 0:
            yield (gi, gj)
            return
        for i in range(gi - r, gi + r + 1):
            yield (i, gj - r)
            yield (i, gj + r)
        for j in range(gj - r + 1, gj + r):
            yield (gi - r, j)
            yield (gi + r, j)

    # -------------------------------------------------------------- snap --
    def _snap(self, lat: float, lng: float, mode_speeds: dict[str, float]) -> _Snap | None:
        """Project (lat, lng) onto the nearest edge legal for this mode.

        Searches the grid outward from the query point's own cell and stops
        as soon as the next ring cannot hold anything closer than the best
        hit so far — the answer is identical to scanning every edge, which
        test_routing pins. Returns None when the mode has no legal edges."""
        if not any(cls in mode_speeds for cls in self._classes):
            return None                       # e.g. a scooter on a footway-only graph
        gi, gj = self._cell(lat, lng)
        # Ring far enough to reach every occupied cell — measured FROM this
        # query, so a point well outside the zone (a rider off the edge of
        # the map) still finds the nearest street instead of falling back
        # to a straight line.
        lo_i, hi_i, lo_j, hi_j = self._grid_bounds
        max_r = max(abs(gi - lo_i), abs(gi - hi_i),
                    abs(gj - lo_j), abs(gj - hi_j))
        best: _Snap | None = None
        seen: set[int] = set()
        r = 0
        while r <= max_r:
            batch = []
            for cell in self._ring(gi, gj, r):
                for i in self._grid.get(cell, ()):
                    if i not in seen:        # an edge spans several cells
                        seen.add(i)
                        batch.append(i)
            if batch:
                best = self._snap_into(lat, lng, mode_speeds, batch, best)
            # cells beyond ring r sit at least r * _GRID_M away, so once the
            # best hit is nearer than that, no further ring can beat it
            if best is not None and best.approach_m <= r * _GRID_M:
                break
            r += 1
        return best

    def _snap_into(self, lat: float, lng: float, mode_speeds: dict[str, float],
                   indices, best: _Snap | None) -> _Snap | None:
        """Project onto each candidate edge, keeping the nearest.

        A local equirectangular frame centred on the query point — exact
        enough at zone scale — with the projection clamped to the segment."""
        m_lng = _M_PER_DEG_LAT * max(0.2, math.cos(math.radians(lat)))
        for i in indices:
            a, b, length, cls, _name = self.edges[i]
            if cls not in mode_speeds:
                continue
            ax, ay = (a[1] - lng) * m_lng, (a[0] - lat) * _M_PER_DEG_LAT
            bx, by = (b[1] - lng) * m_lng, (b[0] - lat) * _M_PER_DEG_LAT
            dx, dy = bx - ax, by - ay
            seg2 = dx * dx + dy * dy
            t = 0.0 if seg2 == 0 else min(1.0, max(0.0, -(ax * dx + ay * dy) / seg2))
            px, py = ax + t * dx, ay + t * dy
            d = math.hypot(px, py)
            if best is None or d < best.approach_m:
                plat = a[0] + t * (b[0] - a[0])
                plng = a[1] + t * (b[1] - a[1])
                best = _Snap(i, plat, plng, a, b, t * length, (1.0 - t) * length, cls, d)
        return best

    # ------------------------------------------------------------- route --
    def route(self, lat1: float, lng1: float, lat2: float, lng2: float,
              mode: str = "scooter") -> tuple[list[tuple[float, float]], float, float]:
        """(waypoints [(lat, lng), ...] starting at EXACTLY (lat1, lng1) and
        ending at EXACTLY (lat2, lng2), total_distance_m, duration_s).

        Fastest path for the mode: A* over travel time, entering/leaving
        the graph at mid-edge projection points. Door-to-road approach
        legs count at walking pace for every mode.

        CONTRACT NOTE — duration_s is the PLANNER's class-weighted estimate
        (main roads faster than lanes). The sim moves riders at the flat
        sim.MODE_SPEED_MPS and derives every user-facing ETA from that same
        flat speed (sim.responders), so displayed ETAs always match actual
        arrival. Do not surface duration_s as an ETA without also moving
        riders at per-class speeds, or the two will drift up to ~75%."""
        wp, dist_m, dur_s, _names = self.route_named(lat1, lng1, lat2, lng2, mode=mode)
        return wp, dist_m, dur_s

    def route_named(self, lat1: float, lng1: float, lat2: float, lng2: float,
                    mode: str = "scooter"
                    ) -> tuple[list[tuple[float, float]], float, float, list[str]]:
        """route() plus per-waypoint street names: names[i] is the name of
        the edge that LEADS INTO waypoints[i] — "" for the first waypoint
        and for the off-road door-to-road approach legs — so callers can
        collapse runs of equal names into turn-by-turn direction steps."""
        speeds = SPEEDS_KMH.get(mode)
        if speeds is None:
            raise ValueError(f"unknown travel mode {mode!r} (want one of {sorted(SPEEDS_KMH)})")

        s = self._snap(lat1, lng1, speeds)
        g = self._snap(lat2, lng2, speeds)
        if s is None or g is None:
            self._note_direct("no snappable edge for mode")
            wp, d, t = self._direct(lat1, lng1, lat2, lng2, speeds)
            return wp, d, t, [""] * len(wp)

        path = self._astar(s, g, speeds)
        if path is None:  # disconnected for this mode — never strand the demo
            self._note_direct("disconnected graph components")
            wp, d, t = self._direct(lat1, lng1, lat2, lng2, speeds)
            return wp, d, t, [""] * len(wp)

        node_seq, road_m, road_s = path
        start_name = self.edges[s.edge_i][4]
        goal_name = self.edges[g.edge_i][4]

        def hop_name(u, v) -> str:
            # Hops out of the snapped start (or into the snapped goal) run
            # along the snapped edge itself; everything else is a real edge.
            if u == _START:
                return start_name
            if v == _GOAL:
                return goal_name
            return self._edge_name.get((min(u, v), max(u, v)), "")

        coords: list[tuple[float, float]] = []
        lead: list[str] = []   # lead[k]: name of the leg arriving at coords[k]
        for j, n in enumerate(node_seq):
            if n == _START:
                coords.append((s.lat, s.lng))
                lead.append("")   # arrived here from the door — approach leg
            else:
                coords.append((g.lat, g.lng) if n == _GOAL else n)
                lead.append(hop_name(node_seq[j - 1], n))

        approach_mps = _APPROACH_KMH / 3.6
        total_m = s.approach_m + road_m + g.approach_m
        total_s = s.approach_m / approach_mps + road_s + g.approach_m / approach_mps

        waypoints = [(lat1, lng1)]
        names = [""]
        for c, nm in zip(coords, lead):
            last = waypoints[-1]
            if abs(c[0] - last[0]) > 1e-9 or abs(c[1] - last[1]) > 1e-9:
                waypoints.append(c)
                names.append(nm)
        last = waypoints[-1]
        if abs(last[0] - lat2) < 1e-9 and abs(last[1] - lng2) < 1e-9 and len(waypoints) > 1:
            waypoints[-1] = (lat2, lng2)  # exact end, not the snapped float twin
        else:
            waypoints.append((lat2, lng2))
            names.append("")              # road-to-door approach leg
        return waypoints, total_m, total_s, names

    def _note_direct(self, reason: str) -> None:
        """A straight-line fallback means a rider will visibly cross ground
        that isn't road — silent on the shipped (fully connected) zone, but
        real OSM imports are frequently disconnected. Warn loudly, once per
        reason, so the failure is a log line instead of a demo mystery."""
        seen = getattr(self, "_direct_warned", None)
        if seen is None:
            seen = self._direct_warned = set()
        if reason not in seen:
            seen.add(reason)
            import sys
            print(f"routing: straight-line fallback in use ({reason}) — "
                  "check the zone with tools/fetch_real_roads.py's "
                  "connectivity report", file=sys.stderr)

    def _direct(self, lat1, lng1, lat2, lng2, speeds) -> tuple[list[tuple[float, float]], float, float]:
        """Straight-line fallback for degenerate cases (no legal edges, or
        start/goal in disconnected components for this mode). Priced at
        the mode's slowest street speed so it never flatters an ETA."""
        d = geo.haversine_m(lat1, lng1, lat2, lng2)
        mps = min(speeds.values()) / 3.6
        return [(lat1, lng1), (lat2, lng2)], d, d / mps

    def _astar(self, s: _Snap, g: _Snap, speeds: dict[str, float]
               ) -> tuple[list, float, float] | None:
        """Time-optimal A* from the snapped start to the snapped goal.

        The two projection points join the graph as virtual nodes: the
        start links out to its edge's endpoints, the goal edge's endpoints
        link into the goal, and when both queries snapped onto the *same*
        edge there is also a direct along-edge hop. Heuristic: straight-
        line distance over the mode's top speed — admissible, so the
        result is exact."""
        def mps(cls: str) -> float:
            return speeds[cls] / 3.6

        # goal-side links, indexed by the real node they leave from
        goal_links: dict[tuple[float, float], list[tuple[str, float, str]]] = {}
        for n, d in ((g.a, g.dist_a), (g.b, g.dist_b)):
            goal_links.setdefault(n, []).append((_GOAL, d, g.cls))

        start_links: list[tuple] = [(s.a, s.dist_a, s.cls), (s.b, s.dist_b, s.cls)]
        if s.edge_i == g.edge_i:
            start_links.append((_GOAL, abs(s.dist_a - g.dist_a), s.cls))

        vmax = max(speeds.values()) / 3.6

        def coord(n):
            if n == _START:
                return (s.lat, s.lng)
            if n == _GOAL:
                return (g.lat, g.lng)
            return n

        def h(n) -> float:
            c = coord(n)
            return geo.haversine_m(c[0], c[1], g.lat, g.lng) / vmax

        best_t: dict = {_START: 0.0}
        came: dict = {}
        tie = 0
        pq: list[tuple[float, int, object]] = [(h(_START), tie, _START)]
        done: set = set()
        while pq:
            _, _, u = heapq.heappop(pq)
            if u in done:
                continue
            done.add(u)
            if u == _GOAL:
                break
            if u == _START:
                nbrs = start_links
            else:
                nbrs = self.adj.get(u, []) + goal_links.get(u, [])
            tu = best_t[u]
            for v, length, cls in nbrs:
                if cls not in speeds:
                    continue  # forbidden for this mode (e.g. scooter on a footway)
                nt = tu + length / mps(cls)
                if nt < best_t.get(v, math.inf) - 1e-12:
                    best_t[v] = nt
                    came[v] = (u, length)
                    tie += 1
                    heapq.heappush(pq, (nt + h(v), tie, v))
        if _GOAL not in done:
            return None
        # walk back, summing metres as we go (times are already in best_t)
        seq: list = [_GOAL]
        dist = 0.0
        while seq[-1] != _START:
            prev, length = came[seq[-1]]
            dist += length
            seq.append(prev)
        seq.reverse()
        return seq, dist, best_t[_GOAL]


def route_remaining_m(waypoints: list[tuple[float, float]], idx: int,
                       cur_lat: float, cur_lng: float) -> float:
    """Distance left to travel: from the current position to waypoints[idx],
    then the rest of the polyline."""
    if idx >= len(waypoints):
        return 0.0
    total = geo.haversine_m(cur_lat, cur_lng, *waypoints[idx])
    for a, b in zip(waypoints[idx:], waypoints[idx + 1:]):
        total += geo.haversine_m(*a, *b)
    return total


# ---------------------------------------------------------------------------
# Legacy fallback: the synthetic mesh (v1). Kept intact so environments
# without pukaar/data/demo_zone.geojson can still route over *something*.
# ---------------------------------------------------------------------------

_BLOCK_M = 170.0          # rough city-block spacing
_ROTATION_DEG = 17.0      # off-axis so it doesn't read as a raw grid
_JITTER_M = 22.0          # per-node wobble, same purpose
_EDGE_DROP_P = 0.06       # fraction of block edges randomly missing
_MESH_SEED = 20260731     # fixed -> identical mesh every run


class RoadMesh:
    """A small routable street graph covering a circular zone."""

    def __init__(self, center_lat: float, center_lng: float, radius_m: float,
                 seed: int = _MESH_SEED):
        self.nodes: dict[int, tuple[float, float]] = {}
        self.adj: dict[int, list[tuple[int, float]]] = {}
        self._build(center_lat, center_lng, radius_m, random.Random(seed))

    # ------------------------------------------------------------- build --
    def _build(self, clat: float, clng: float, radius_m: float, rng: random.Random) -> None:
        span = radius_m * 1.4                       # margin past the zone circle
        half = max(3, int(span / _BLOCK_M))
        rot = math.radians(_ROTATION_DEG)
        cos_r, sin_r = math.cos(rot), math.sin(rot)

        grid_id: dict[tuple[int, int], int] = {}
        for i in range(-half, half + 1):
            for j in range(-half, half + 1):
                x = i * _BLOCK_M + rng.uniform(-_JITTER_M, _JITTER_M)
                y = j * _BLOCK_M + rng.uniform(-_JITTER_M, _JITTER_M)
                east = x * cos_r - y * sin_r
                north = x * sin_r + y * cos_r
                lat, lng = geo.offset_m(clat, clng, north, east)
                nid = len(self.nodes)
                grid_id[(i, j)] = nid
                self.nodes[nid] = (lat, lng)
                self.adj[nid] = []

        def link(a: int, b: int) -> None:
            d = geo.haversine_m(*self.nodes[a], *self.nodes[b])
            self.adj[a].append((b, d))
            self.adj[b].append((a, d))

        edges: list[tuple[int, int]] = []
        for (i, j), nid in grid_id.items():
            for ni, nj in ((i + 1, j), (i, j + 1)):
                other = grid_id.get((ni, nj))
                if other is not None:
                    edges.append((nid, other))
        for a, b in edges:
            if rng.random() >= _EDGE_DROP_P:
                link(a, b)

        self._ensure_connected(rng)

    def _ensure_connected(self, rng: random.Random) -> None:
        """Random edge-dropping is far below the grid's percolation
        threshold so this should be a no-op in practice, but a demo must
        never ship a stranded node — reconnect any extra component to the
        main one via its closest cross-component node pair."""
        components = self._components()
        if len(components) <= 1:
            return
        components.sort(key=len, reverse=True)
        main = components[0]
        for stray in components[1:]:
            best = None
            for a in stray:
                for b in main:
                    d = geo.haversine_m(*self.nodes[a], *self.nodes[b])
                    if best is None or d < best[0]:
                        best = (d, a, b)
            d, a, b = best
            self.adj[a].append((b, d))
            self.adj[b].append((a, d))
            main = main | stray

    def _components(self) -> list[set[int]]:
        seen: set[int] = set()
        out: list[set[int]] = []
        for start in self.nodes:
            if start in seen:
                continue
            comp, stack = {start}, [start]
            while stack:
                u = stack.pop()
                for v, _ in self.adj[u]:
                    if v not in comp:
                        comp.add(v)
                        stack.append(v)
            seen |= comp
            out.append(comp)
        return out

    # ------------------------------------------------------------- query --
    def nearest_node(self, lat: float, lng: float) -> int:
        return min(self.nodes, key=lambda nid: geo.haversine_m(lat, lng, *self.nodes[nid]))

    def route(self, lat1: float, lng1: float, lat2: float, lng2: float
              ) -> tuple[list[tuple[float, float]], float]:
        """Waypoints from (lat1,lng1) to (lat2,lng2) via the mesh, and the
        total path distance in metres (door-to-node + mesh + node-to-door)."""
        start, goal = self.nearest_node(lat1, lng1), self.nearest_node(lat2, lng2)
        node_path, mesh_dist = self._dijkstra(start, goal)
        waypoints = [(lat1, lng1)] + [self.nodes[n] for n in node_path] + [(lat2, lng2)]
        total = (mesh_dist
                 + geo.haversine_m(lat1, lng1, *self.nodes[start])
                 + geo.haversine_m(lat2, lng2, *self.nodes[goal]))
        return waypoints, total

    def _dijkstra(self, start: int, goal: int) -> tuple[list[int], float]:
        dist: dict[int, float] = {start: 0.0}
        prev: dict[int, int] = {}
        pq: list[tuple[float, int]] = [(0.0, start)]
        visited: set[int] = set()
        while pq:
            d, u = heapq.heappop(pq)
            if u in visited:
                continue
            visited.add(u)
            if u == goal:
                break
            for v, w in self.adj[u]:
                nd = d + w
                if nd < dist.get(v, math.inf):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))
        path = [goal]
        while path[-1] != start:
            path.append(prev[path[-1]])
        path.reverse()
        return path, dist.get(goal, 0.0)
