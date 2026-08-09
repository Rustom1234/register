"""Fetch real OSM streets/parks/water/rail/buildings and write the map data.

This is the importer behind both committed map files. It queries the
Overpass API once per profile and converts the answer into the exact
FeatureCollection schema the demo expects:

  * roads      LineString, class primary/secondary/residential/lane/footway
  * areas      Polygon, kind park/water/rail/campus
  * buildings  Polygon, kind building
  * landmarks  Point, kind landmark (named node OR the centroid of a named
               historic/park/station area, so Humayun's Tomb and Sunder
               Nursery get labels even though OSM maps them as areas)
  * places     Point, kind place, rank 1 (district) / 2 (neighbourhood)

Two profiles:

    --profile zone   the pilot area that FEEDS THE ROUTER. Full detail,
                     clipped to a disc, thinned, and pruned to a single
                     connected component (see prune_to_one_component).
    --profile city   the scenery around it. Arterials only, clipped to the
                     camera-clamp square MINUS the zone disc, so the two
                     tiers tile instead of overlapping and every corner the
                     founder can pan to has real streets in it.

Usage:
    python tools/fetch_real_roads.py --profile zone \
        --out pukaar/data/demo_zone.geojson
    python tools/fetch_real_roads.py --profile city \
        --out pukaar/data/demo_city.geojson

Data © OpenStreetMap contributors, ODbL — the attribution travels in the
file's "note"/"attribution" keys and is shown on every map surface. Keep
it if you ship the output.

The pure helpers (road_class, area_kind, landmark_icon, clipping, thinning
and component pruning) are covered by tests/test_demo_zone.py; only the
network call itself is untested by design.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
TIMEOUT_S = 180

# Roads a rider can actually be sent down. Anything not in this table is
# not a road for us (a waterway, a wall, a proposed alignment).
_ROAD_CLASS = {
    "motorway": "primary", "trunk": "primary", "primary": "primary",
    "secondary": "secondary", "tertiary": "secondary",
    "residential": "residential", "unclassified": "residential",
    "living_street": "residential",
    "service": "lane", "track": "lane",
    "footway": "footway", "path": "footway", "pedestrian": "footway",
    "steps": "footway", "bridleway": "footway", "cycleway": "footway",
    "corridor": "footway",
}

# The city tier draws only the roads you would still see on a zoomed-out
# map — everything else is noise at that scale (and weight on the wire).
_CITY_CLASSES = {"primary", "secondary"}


def road_class(tags: dict | None) -> str | None:
    """OSM tags -> demo-zone road class, or None for non-roads.

    '_link' variants map with their parent (primary_link -> primary).
    highway=construction/proposed are deliberately absent: a rider must
    never be routed down a street that is not open."""
    hw = (tags or {}).get("highway", "")
    return _ROAD_CLASS.get(hw.removesuffix("_link"))


def area_kind(tags: dict | None) -> str | None:
    """OSM tags -> demo-zone area kind (park/water/rail/campus), or None."""
    t = tags or {}
    if t.get("leisure") in ("park", "garden", "nature_reserve"):
        return "park"
    if t.get("natural") in ("water", "wood") or t.get("waterway") in ("riverbank", "dock") \
            or t.get("landuse") in ("reservoir", "basin"):
        return "water" if t.get("natural") != "wood" else "park"
    if t.get("landuse") in ("forest", "grass") or t.get("natural") == "grassland":
        return "park"
    if t.get("landuse") == "railway" or t.get("railway") in ("rail", "yard", "station_area"):
        return "rail"
    if t.get("amenity") in ("university", "college", "school") \
            or t.get("landuse") == "education":
        return "campus"
    return None


def landmark_icon(tags: dict | None) -> str | None:
    """OSM tags -> demo-zone landmark icon, or None to skip the feature.

    A dargah is a mosque before it is a monument, so place_of_worship is
    tested ahead of historic — otherwise Nizamuddin Dargah, which carries
    both tags, would read as a generic monument."""
    t = tags or {}
    if t.get("railway") == "station":
        return "rail"
    if t.get("amenity") == "place_of_worship" and t.get("religion") == "muslim":
        return "mosque"
    if t.get("historic") in ("monument", "tomb", "memorial", "fort",
                             "archaeological_site", "ruins", "city_gate"):
        return "monument"
    if t.get("amenity") == "place_of_worship":
        return "monument"
    if t.get("amenity") in ("hospital", "clinic"):
        return "hospital"
    if t.get("amenity") == "marketplace":
        return "market"
    if t.get("leisure") in ("park", "garden"):
        return "park"
    if t.get("tourism") == "attraction":
        return "monument"
    return None


def place_rank(tags: dict | None) -> int | None:
    """OSM place=* -> label rank: 1 holds at the furthest zoom, 2 fades in."""
    p = (tags or {}).get("place")
    if p in ("city", "town", "suburb"):
        return 1
    if p in ("neighbourhood", "village", "quarter"):
        return 2
    return None


# --------------------------------------------------------------- geometry --
_M_PER_DEG_LAT = 111_320.0


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p = math.pi / 180
    a = (0.5 - math.cos((lat2 - lat1) * p) / 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lng2 - lng1) * p)) / 2)
    return 12_742_000 * math.asin(math.sqrt(max(0.0, a)))


def _local_m(lng: float, lat: float, clat: float, clng: float) -> tuple[float, float]:
    """[lng, lat] -> metres east/north of the profile centre."""
    return ((lng - clng) * _M_PER_DEG_LAT * math.cos(math.radians(clat)),
            (lat - clat) * _M_PER_DEG_LAT)


def ring_area_m2(ring: list[list[float]], clat: float, clng: float) -> float:
    """Shoelace area of a closed ring, in square metres."""
    pts = [_local_m(x, y, clat, clng) for x, y in ring]
    s = sum(pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1]
            for i in range(len(pts) - 1))
    return abs(s) / 2.0


def ring_centroid(ring: list[list[float]]) -> list[float]:
    """Area-weighted centroid of a closed ring, as [lng, lat]."""
    a = sx = sy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        cross = x1 * y2 - x2 * y1
        a += cross
        sx += (x1 + x2) * cross
        sy += (y1 + y2) * cross
    if abs(a) < 1e-12:                      # degenerate ring — plain mean
        pts = ring[:-1] or ring
        return [sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)]
    return [sx / (3 * a), sy / (3 * a)]


def region(profile: str, clat: float, clng: float, r_in: float, r_out: float):
    """The keep-region predicate for a profile, over [lng, lat] points.

    zone  a disc of radius r_out around the centre.
    city  the camera-clamp SQUARE of half-width r_out, minus the disc of
          radius r_in that the zone tier already covers. A square, not a
          disc, because the map clamps panning to a square: clip to a disc
          and the corners of what the founder can pan to are empty.
    """
    def inside(p):
        d = _haversine_m(clat, clng, p[1], p[0])
        if profile == "zone":
            return d <= r_out
        x, y = _local_m(p[0], p[1], clat, clng)
        return d >= r_in and max(abs(x), abs(y)) <= r_out
    return inside


def clip_line(pts: list[list[float]], inside) -> list[list[list[float]]]:
    """Split a LineString to the parts inside a keep-region predicate.

    Overpass 'out geom' returns whole ways, so a street touching the query
    area arrives with kilometres of geometry outside it. Crossings are
    interpolated so a clipped street still ends exactly on the boundary
    instead of at whichever vertex happened to be last."""
    out: list[list[list[float]]] = []
    run: list[list[float]] = []
    for a, b in zip(pts, pts[1:]):
        ia, ib = inside(a), inside(b)
        if ia:
            if not run:
                run = [a]
            elif run[-1] != a:
                run.append(a)
        if ia != ib:
            # binary-search the boundary crossing to ~10 cm
            lo, hi = 0.0, 1.0
            for _ in range(24):
                mid = (lo + hi) / 2
                m = [a[0] + (b[0] - a[0]) * mid, a[1] + (b[1] - a[1]) * mid]
                if inside(m) == ia:
                    lo = mid
                else:
                    hi = mid
            t = (lo + hi) / 2
            cross = [round(a[0] + (b[0] - a[0]) * t, 7),
                     round(a[1] + (b[1] - a[1]) * t, 7)]
            if ia:
                run.append(cross)
                if len(run) >= 2:
                    out.append(run)
                run = []
            else:
                run = [cross]
    if pts and inside(pts[-1]) and run:
        if run[-1] != pts[-1]:
            run.append(pts[-1])
        if len(run) >= 2:
            out.append(run)
    return [ln for ln in out if len(ln) >= 2]


def simplify(pts: list[list[float]], tol_m: float, clat: float,
             clng: float) -> list[list[float]]:
    """Ramer-Douglas-Peucker in local metres, keeping both endpoints.

    Only ever applied to geometry that is DRAWN and never routed (city
    scenery, building footprints, park outlines). The pilot zone's roads
    are left at full fidelity — the router measures real distances on
    them, and a shortcut here would become a wrong ETA there."""
    if len(pts) < 3:
        return pts
    loc = [_local_m(x, y, clat, clng) for x, y in pts]

    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        (ax, ay), (bx, by) = loc[i], loc[j]
        dx, dy = bx - ax, by - ay
        span = math.hypot(dx, dy)
        best, best_k = -1.0, -1
        for k in range(i + 1, j):
            px, py = loc[k]
            if span < 1e-9:
                d = math.hypot(px - ax, py - ay)
            else:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (span * span)))
                d = math.hypot(px - ax - t * dx, py - ay - t * dy)
            if d > best:
                best, best_k = d, k
        if best > tol_m:
            keep[best_k] = True
            stack.append((i, best_k))
            stack.append((best_k, j))
    return [p for p, k in zip(pts, keep) if k]


def _round_line(pts: list[list[float]], nd: int) -> list[list[float]]:
    """Round and drop consecutive duplicates created by the rounding."""
    out: list[list[float]] = []
    for x, y in pts:
        p = [round(x, nd), round(y, nd)]
        if not out or out[-1] != p:
            out.append(p)
    return out


def thin_roads(roads: list[dict], min_gap_m: float = 1.5) -> None:
    """Drop road vertices closer than min_gap_m, in place.

    OSM traces curves with vertices centimetres apart; the router turns
    every pair into an edge, so the graph bloats and near-zero-length
    edges appear. Junctions — any vertex shared by two ways, plus every
    way endpoint — are never dropped, because thinning one away on one
    side of a crossing would silently disconnect the network."""
    seen: dict[tuple[float, float], int] = {}
    for f in roads:
        for c in f["geometry"]["coordinates"]:
            k = (c[0], c[1])
            seen[k] = seen.get(k, 0) + 1
    for f in roads:
        cs = f["geometry"]["coordinates"]
        keep = [cs[0]]
        for p in cs[1:-1]:
            shared = seen.get((p[0], p[1]), 0) > 1
            if shared or _haversine_m(keep[-1][1], keep[-1][0], p[1], p[0]) >= min_gap_m:
                keep.append(p)
        last = cs[-1]
        # An endpoint closer than the gap to the previous kept vertex would
        # make a degenerate edge; drop that neighbour instead of the
        # endpoint, which may be someone else's junction.
        while len(keep) > 1 and \
                _haversine_m(keep[-1][1], keep[-1][0], last[1], last[0]) < min_gap_m and \
                seen.get((keep[-1][0], keep[-1][1]), 0) <= 1:
            keep.pop()
        keep.append(last)
        f["geometry"]["coordinates"] = keep


def merge_close_nodes(roads: list[dict], tol_m: float = 1.2) -> list[dict]:
    """Weld road vertices that sit within tol_m of each other, in place.

    Surveyors sometimes place two nodes a few centimetres apart at the same
    junction (a slip road meeting a carriageway, a footway landing on a
    kerb). Left alone those become sub-metre edges the router has to walk,
    and — worse — two vertices that LOOK like one junction but are not
    actually connected. Welding them makes the crossing real.

    Ways that collapse below two distinct points are dropped."""
    grid: dict[tuple[int, int], list[tuple[float, float]]] = {}
    canon: dict[tuple[float, float], tuple[float, float]] = {}
    cell = tol_m / _M_PER_DEG_LAT * 2          # in degrees, generous

    pts = {(c[0], c[1]) for f in roads for c in f["geometry"]["coordinates"]}
    for p in sorted(pts):                      # sorted => deterministic winner
        gi, gj = int(p[0] / cell), int(p[1] / cell)
        hit = None
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for q in grid.get((gi + di, gj + dj), ()):
                    if _haversine_m(p[1], p[0], q[1], q[0]) <= tol_m:
                        hit = q
                        break
                if hit:
                    break
            if hit:
                break
        if hit is None:
            grid.setdefault((gi, gj), []).append(p)
            canon[p] = p
        else:
            canon[p] = canon[hit]

    kept = []
    for f in roads:
        out: list[list[float]] = []
        for c in f["geometry"]["coordinates"]:
            p = list(canon[(c[0], c[1])])
            if not out or out[-1] != p:
                out.append(p)
        if len(out) >= 2:
            f["geometry"]["coordinates"] = out
            kept.append(f)
    return kept


def _segments(f: dict):
    cs = f["geometry"]["coordinates"]
    return list(zip(cs, cs[1:]))


def _components(edges) -> list[set]:
    adj: dict[tuple, set] = {}
    for a, b in edges:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    seen, comps = set(), []
    for start in adj:
        if start in seen:
            continue
        comp, stack = {start}, [start]
        seen.add(start)
        while stack:
            for n in adj[stack.pop()]:
                if n not in seen:
                    seen.add(n)
                    comp.add(n)
                    stack.append(n)
        comps.append(comp)
    return comps


def prune_to_one_component(roads: list[dict]) -> list[dict]:
    """Keep only the roads a rider can actually reach.

    Clipping a real street network at a radius leaves orphans: a cul-de-sac
    whose only link left the disc, a service road reachable only over a
    flyover that was cut. The router would answer such a query with a
    straight line — a rider 'flying' over blocks. So:

      1. take the largest connected component of the DRIVEABLE network
         (everything except footways) — that is the scooter mesh;
      2. drop driveable roads outside it;
      3. keep footways only where they hang off that mesh.

    The result satisfies both invariants the router needs: the whole
    network is one component, and so is the footway-free subgraph."""
    def key(p):
        return (p[0], p[1])

    drive = [f for f in roads if f["properties"]["class"] != "footway"]
    foot = [f for f in roads if f["properties"]["class"] == "footway"]

    drive_edges = [(key(a), key(b)) for f in drive for a, b in _segments(f)]
    comps = _components(drive_edges)
    if not comps:
        return []
    mesh = max(comps, key=len)
    drive = [f for f in drive
             if all(key(a) in mesh and key(b) in mesh for a, b in _segments(f))]

    all_edges = [(key(a), key(b)) for f in drive + foot for a, b in _segments(f)]
    whole = next((c for c in _components(all_edges) if c & mesh), mesh)
    foot = [f for f in foot
            if all(key(a) in whole and key(b) in whole for a, b in _segments(f))]
    return drive + foot


# ----------------------------------------------------------------- queries --
def zone_query(lat: float, lng: float, radius: int) -> str:
    around = f"(around:{radius},{lat},{lng})"
    return f"""[out:json][timeout:{TIMEOUT_S - 20}];
(
  way["highway"]{around};
  way["building"]{around};
  way["leisure"~"^(park|garden|nature_reserve)$"]{around};
  way["natural"~"^(water|wood|grassland)$"]{around};
  way["waterway"~"^(riverbank|dock)$"]{around};
  way["landuse"~"^(railway|reservoir|basin|education|forest|grass)$"]{around};
  way["railway"~"^(rail|yard|station_area)$"]{around};
  way["amenity"~"^(university|college|school)$"]{around};
  node["railway"="station"]{around};
  node["historic"]{around};
  node["amenity"~"^(place_of_worship|hospital|clinic|marketplace)$"]{around};
);
out tags geom;"""


def city_query(lat: float, lng: float, radius: int) -> str:
    around = f"(around:{radius},{lat},{lng})"
    return f"""[out:json][timeout:{TIMEOUT_S - 20}];
(
  way["highway"~"^(motorway|trunk|primary|secondary)(_link)?$"]{around};
  way["natural"="water"]{around};
  way["waterway"="riverbank"]{around};
  way["leisure"~"^(park|nature_reserve)$"]{around};
  way["landuse"~"^(railway|forest)$"]{around};
  node["place"~"^(city|town|suburb|neighbourhood)$"]{around};
);
out tags geom;"""


def _fetch(query: str) -> dict:
    body = urllib.parse.urlencode({"data": query}).encode()
    last_err: Exception | None = None
    for attempt in (1, 2, 3):
        try:
            req = urllib.request.Request(
                OVERPASS_URL, data=body,
                headers={"User-Agent": "pukaar-demo-zone/0.1"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return json.load(resp)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                json.JSONDecodeError, ConnectionError) as e:
            last_err = e
            if attempt < 3:
                wait = 10 * attempt
                print(f"overpass attempt {attempt} failed ({e}); "
                      f"retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
    raise SystemExit(
        f"error: could not reach the Overpass API: {last_err}\n"
        "Check your network, or try again later — Overpass rate-limits "
        "busy periods and returns 429 when it is loaded.")


# -------------------------------------------------------------- conversion --
def convert(elements: list[dict], *, profile: str, lat: float, lng: float,
            r_in: float, r_out: float,
            min_park_m2: float | None = None,
            min_water_m2: float | None = None,
            min_building_m2: float = 20.0,
            min_landmark_park_m2: float = 6_000.0) -> list[dict]:
    """Overpass 'out geom' elements -> map-file features for one profile.

    The city tier is drawn at 10 km out, so it drops anything too small to
    read at that scale and simplifies what is left; the zone tier keeps
    its roads exact because the router measures on them."""
    zone = profile == "zone"
    road_nd = 6 if zone else 5                # 6 dp keeps shared junctions exact
    area_nd = 5
    # tolerances in metres: 0 = no simplification
    road_tol = 0.0 if zone else 9.0
    area_tol = 1.0 if zone else 12.0
    if min_park_m2 is None:
        min_park_m2 = 400.0 if zone else 40_000.0
    if min_water_m2 is None:
        min_water_m2 = 200.0 if zone else 20_000.0
    roads: list[dict] = []
    others: list[dict] = []

    inside = region(profile, lat, lng, r_in, r_out)

    def in_range(x, y):
        return inside([x, y])

    for el in elements:
        tags = el.get("tags", {})
        etype = el.get("type")
        if etype == "way" and el.get("geometry"):
            pts = [[p["lon"], p["lat"]] for p in el["geometry"]]
            cls = road_class(tags)
            if cls is not None:
                if profile == "city" and cls not in _CITY_CLASSES:
                    continue
                for part in clip_line(pts, inside):
                    if road_tol:
                        part = simplify(part, road_tol, lat, lng)
                    line = _round_line(part, road_nd)
                    if len(line) < 2:
                        continue
                    props = {"kind": "road", "class": cls}
                    if tags.get("name"):
                        props["name"] = tags["name"]
                    roads.append({"type": "Feature", "properties": props,
                                  "geometry": {"type": "LineString",
                                               "coordinates": line}})
                continue

            # Railways are LINEAR in OSM — there is no corridor polygon to
            # import. They are drawn (dashed) and never routed: "rail" is
            # not a road class, so a rider can never be sent down a track.
            if tags.get("railway") in ("rail", "light_rail", "subway", "monorail"):
                if profile != "zone":
                    continue
                for part in clip_line(pts, inside):
                    line = _round_line(simplify(part, max(area_tol, 2.0), lat, lng),
                                       area_nd)
                    if len(line) < 2:
                        continue
                    props = {"kind": "rail"}
                    if tags.get("name"):
                        props["name"] = tags["name"]
                    others.append({"type": "Feature", "properties": props,
                                   "geometry": {"type": "LineString",
                                                "coordinates": line}})
                continue

            closed = len(pts) >= 4 and pts[0] == pts[-1]
            if not closed:
                continue
            # Areas are drawn, not routed: keep the ones whose centre is in
            # range rather than clipping the ring (a half-clipped park is a
            # worse lie than one that overhangs the edge by a few metres).
            cx, cy = ring_centroid(pts)
            if not in_range(cx, cy):
                continue
            ring = _round_line(simplify(pts, area_tol, lat, lng), area_nd)
            if len(ring) < 4:
                continue
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            area = ring_area_m2(ring, lat, lng)
            kind = area_kind(tags)
            is_building = "building" in tags and kind is None

            if is_building:
                if profile == "city" or area < min_building_m2:
                    continue
                others.append({"type": "Feature",
                               "properties": {"kind": "building"},
                               "geometry": {"type": "Polygon",
                                            "coordinates": [ring]}})
            elif kind is not None:
                if kind == "park" and area < min_park_m2:
                    continue
                if kind == "water" and area < min_water_m2:
                    continue
                props = {"kind": kind}
                if tags.get("name"):
                    props["name"] = tags["name"]
                others.append({"type": "Feature", "properties": props,
                               "geometry": {"type": "Polygon",
                                            "coordinates": [ring]}})

            # A named area can ALSO earn a label — Humayun's Tomb and Sunder
            # Nursery are areas in OSM, and a map of Nizamuddin without them
            # is not a map of Nizamuddin.
            icon = landmark_icon(tags)
            if profile == "zone" and icon and tags.get("name") \
                    and not (icon == "park" and area < min_landmark_park_m2):
                others.append({
                    "type": "Feature",
                    "properties": {"kind": "landmark", "name": tags["name"],
                                   "icon": icon},
                    "geometry": {"type": "Point",
                                 "coordinates": _round_line(
                                     [ring_centroid(ring)], area_nd)[0]}})

        elif etype == "node":
            x, y = el.get("lon"), el.get("lat")
            if x is None or not in_range(x, y):
                continue
            pt = [round(x, area_nd), round(y, area_nd)]
            rank = place_rank(tags)
            if profile == "city":
                if rank and tags.get("name"):
                    others.append({
                        "type": "Feature",
                        "properties": {"kind": "place", "name": tags["name"],
                                       "rank": rank},
                        "geometry": {"type": "Point", "coordinates": pt}})
                continue
            icon = landmark_icon(tags)
            if icon and tags.get("name"):
                others.append({
                    "type": "Feature",
                    "properties": {"kind": "landmark", "name": tags["name"],
                                   "icon": icon},
                    "geometry": {"type": "Point", "coordinates": pt}})

    if zone:
        # weld -> thin -> prune: welding first makes near-coincident
        # junctions into real crossings, so pruning does not throw away a
        # block that was only ever "disconnected" by a 20 cm survey gap.
        roads = merge_close_nodes(roads)
        thin_roads(roads)
        roads = prune_to_one_component(roads)

    others = _dedupe_landmarks(others)
    # Stable order so a re-fetch diffs as data changes, not as reshuffling.
    return sorted(roads + others,
                  key=lambda f: (f["properties"]["kind"],
                                 f["properties"].get("name") or "",
                                 json.dumps(f["geometry"]["coordinates"])))


def _dedupe_landmarks(feats: list[dict]) -> list[dict]:
    """One label per name — OSM often carries a node AND an area for the
    same place (a station node inside a station area)."""
    out, seen = [], set()
    for f in feats:
        p = f["properties"]
        if p["kind"] not in ("landmark", "place"):
            out.append(f)
            continue
        k = (p["kind"], p["name"])
        if k in seen:
            continue
        seen.add(k)
        out.append(f)
    return out


NOTE = ("Real OpenStreetMap data (c) OpenStreetMap contributors, ODbL, "
        "imported by tools/fetch_real_roads.py — NOT a hand-drawn or "
        "invented map.")


def build(elements: list[dict], *, profile: str, lat: float, lng: float,
          r_in: float, r_out: float, fetched: str | None = None) -> dict:
    features = convert(elements, profile=profile, lat=lat, lng=lng,
                       r_in=r_in, r_out=r_out)
    return {
        "type": "FeatureCollection",
        "note": NOTE,
        "attribution": "(c) OpenStreetMap contributors",
        "license": "ODbL 1.0 (https://opendatacommons.org/licenses/odbl/)",
        "source": {"api": OVERPASS_URL, "profile": profile,
                   "center": [round(lng, 6), round(lat, 6)],
                   "radius_m": [int(r_in), int(r_out)],
                   "fetched": fetched},
        "features": features,
    }


def render(fc: dict) -> str:
    return json.dumps(fc, ensure_ascii=False, separators=(",", ":")) + "\n"


PROFILES = {
    # profile: (Overpass radius, keep from, keep to)
    #
    # zone: fetch a little wider than we keep, so streets are clipped at a
    #   clean boundary rather than ending wherever the query disc did.
    # city: keep the +/-10 km camera-clamp square (CITY_HALF_M in app.js /
    #   witness.js), so fetch the disc that CONTAINS that square —
    #   10000 * sqrt(2) = 14143 m, plus a margin.
    "zone": (1800, 0.0, 1600.0),
    "city": (14300, 1600.0, 10000.0),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--profile", choices=sorted(PROFILES), default="zone")
    ap.add_argument("--lat", type=float, default=28.5933)
    ap.add_argument("--lng", type=float, default=77.2507)
    ap.add_argument("--radius", type=int, default=None,
                    help="override the profile's outer radius, in metres")
    ap.add_argument("--raw", type=Path, default=None,
                    help="read a cached Overpass response instead of "
                         "querying (and write it there on a live fetch)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    fetch_r, r_in, r_out = PROFILES[args.profile]
    if args.radius is not None:
        if not 50 <= args.radius <= 20_000:
            raise SystemExit("error: --radius must be 50..20000 metres")
        r_out = float(args.radius)
        fetch_r = int(r_out * 1.15)

    if args.raw and args.raw.exists():
        print(f"reading cached Overpass response {args.raw}", file=sys.stderr)
        data = json.loads(args.raw.read_text(encoding="utf-8"))
        fetched = None
    else:
        q = (zone_query if args.profile == "zone" else city_query)(
            args.lat, args.lng, fetch_r)
        print(f"querying Overpass for the {args.profile} profile: "
              f"{fetch_r} m around {args.lat},{args.lng} ...", file=sys.stderr)
        data = _fetch(q)
        fetched = time.strftime("%Y-%m-%d", time.gmtime())
        if args.raw:
            args.raw.write_text(json.dumps(data))

    fc = build(data.get("elements", []), profile=args.profile, lat=args.lat,
               lng=args.lng, r_in=r_in, r_out=r_out, fetched=fetched)
    if not fc["features"]:
        raise SystemExit("error: Overpass returned no usable features — "
                         "check the coordinates and radius.")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(fc), encoding="utf-8")

    counts: dict[str, int] = {}
    for f in fc["features"]:
        counts[f["properties"]["kind"]] = counts.get(f["properties"]["kind"], 0) + 1
    summary = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
    print(f"wrote {args.out} — {len(fc['features'])} features "
          f"({summary}), {args.out.stat().st_size:,} bytes")
    if args.profile == "zone":
        _connectivity_report(args.out)


def _connectivity_report(path: Path) -> None:
    """Per-mode sanity check the router relies on: a mode with disconnected
    islands silently degrades to straight-line (_direct) fallbacks in the
    sim, so warn loudly here where the founder can see it, rather than let
    riders 'fly' across gaps at run time."""
    try:
        import random
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from pukaar import routing
    except Exception as exc:  # tool must still succeed if the pkg isn't importable
        print(f"(connectivity check skipped: {exc})", file=sys.stderr)
        return
    graph = routing.RoadGraph(path)
    lats = [n[0] for n in graph.nodes] or [0]
    lngs = [n[1] for n in graph.nodes] or [0]
    box = (min(lats), max(lats), min(lngs), max(lngs))
    rng = random.Random(1)
    for mode in ("walk", "cycle", "scooter"):
        direct = 0
        N = 200
        for _ in range(N):
            a = (rng.uniform(box[0], box[1]), rng.uniform(box[2], box[3]))
            b = (rng.uniform(box[0], box[1]), rng.uniform(box[2], box[3]))
            wps, _d, _t = graph.route(a[0], a[1], b[0], b[1], mode=mode)
            if len(wps) <= 2:
                direct += 1
        pct = 100 * direct / N
        flag = "  ⚠ disconnected islands — routing will use straight lines" if pct > 5 else ""
        print(f"connectivity [{mode:7s}]: {pct:.0f}% straight-line fallback{flag}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
