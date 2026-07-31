"""Offline routing over a locally-generated street mesh.

There is no reachable live map/routing API from this environment (the
sandbox's network policy blocks OSM/Overpass), so responders can't be
routed over surveyed road geometry. Instead this module deterministically
generates a locally-coherent grid of streets around the demo zone —
rotated and lightly jittered so it doesn't read as a raw graph-paper
grid, with a random scattering of missing block-edges — and does real
Dijkstra shortest-path routing over it. The result is genuine pathfinding
and genuine distances (longer than straight-line, the way real streets
are), just not a replica of Nizamuddin's actual streets. Zero network
calls, zero dependencies beyond the stdlib.
"""

from __future__ import annotations

import heapq
import math
import random

from . import geo

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
