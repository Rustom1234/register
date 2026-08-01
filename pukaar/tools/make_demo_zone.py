"""Generate pukaar/data/demo_zone.geojson — the demo-zone street network.

A representative, Nizamuddin-INSPIRED district (the sandbox blocks OSM, so
this is hand-planned geometry, not surveyed map data): Mathura Road as the
curved primary artery, Lodhi Road east-west in the north, a rail corridor
through the south-east with exactly two road crossings, Humayun's Tomb and
Sunder Nursery as road-free parks, a dense irregular basti of lanes and
footways around the Dargah, and the calmer planned grid of Nizamuddin East
between the rail and the Tomb. Building footprints — small jittered quads
roughly parallel to their street — line the residential roads and lanes,
packed tight in the basti and sparser in the Nizamuddin East blocks.

Everything is planned in local metres (x east, y north of the zone center)
and converted to lat/lng with pukaar.geo.offset_m, rounded to 6 decimal
places. Junction vertices are deduplicated by their rounded coordinate, so
roads that meet really do share exact vertices — the connectivity contract
the router relies on.

Deterministic: a fixed seed drives all jitter, so re-running the script
reproduces the committed file byte-for-byte.

Usage: python tools/make_demo_zone.py [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pukaar import geo  # noqa: E402  (path bootstrap above)

SEED = 20260801
CLAT, CLNG = 28.5933, 77.2507
NOTE = ("Representative demo geometry inspired by the Nizamuddin area — NOT "
        "surveyed map data. Swap in real OSM data via tools/fetch_real_roads.py.")
OUT = Path(__file__).resolve().parents[1] / "pukaar" / "data" / "demo_zone.geojson"


def _lnglat(x: float, y: float) -> tuple[float, float]:
    """Local metres (east, north of zone center) -> rounded [lng, lat]."""
    lat, lng = geo.offset_m(CLAT, CLNG, y, x)
    return (round(lng, 6), round(lat, 6))


class Net:
    """Road-network builder: nodes deduped by rounded lng/lat, roads as
    node-id polylines, plus the graph checks the schema contract demands."""

    def __init__(self) -> None:
        self._by_coord: dict[tuple[float, float], int] = {}
        self.coords: list[tuple[float, float]] = []   # id -> (lng, lat)
        self.meters: list[tuple[float, float]] = []   # id -> (x, y)
        self.roads: list[dict] = []                   # {nodes, cls, name}

    def node(self, x: float, y: float) -> int:
        c = _lnglat(x, y)
        nid = self._by_coord.get(c)
        if nid is None:
            nid = len(self.coords)
            self._by_coord[c] = nid
            self.coords.append(c)
            self.meters.append((x, y))
        return nid

    def road(self, pts: list, cls: str, name: str | None = None) -> dict:
        """pts: mix of (x, y) metre tuples and existing node ids."""
        nodes = [p if isinstance(p, int) else self.node(*p) for p in pts]
        r = {"nodes": nodes, "cls": cls, "name": name}
        self.roads.append(r)
        return r

    # ----------------------------------------------------------- graph --
    def _components(self, roads: list[dict]) -> int:
        adj: dict[int, set[int]] = {}
        for r in roads:
            for a, b in zip(r["nodes"], r["nodes"][1:]):
                adj.setdefault(a, set()).add(b)
                adj.setdefault(b, set()).add(a)
        seen: set[int] = set()
        comps = 0
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

    def all_connected(self, skip: list[dict] | None = None) -> bool:
        drop = {id(r) for r in (skip or [])}
        return self._components([r for r in self.roads if id(r) not in drop]) == 1

    def scooter_connected(self, skip: list[dict] | None = None) -> bool:
        drop = {id(r) for r in (skip or [])}
        keep = [r for r in self.roads
                if r["cls"] != "footway" and id(r) not in drop]
        return self._components(keep) == 1


# -------------------------------------------------------------- layout --
# Mathura Road: primary, gently curved NW-SE through the east of the zone.
# Named vertices below double as junctions for everything that meets it.
MATHURA = [(-50, 1750), (10, 1420), (50, 1150), (120, 860), (180, 600),
           (250, 300), (300, 50), (340, -180), (363, -380), (380, -500),
           (407, -800), (430, -1050), (457, -1350), (480, -1600),
           (505, -1850), (520, -2000)]
LODHI = [(-1650, 980), (-1370, 1000), (-1100, 1020), (-800, 1045),
         (-500, 1060), (-220, 1100), (50, 1150)]
WEST_MARG = [(-1100, 1020), (-1180, 700), (-1220, 400), (-1220, 50),
             (-1160, -300), (-1000, -620), (-750, -830), (-450, -950),
             (-100, -1040), (150, -1000), (300, -910), (407, -800)]

# Rail corridor: thin band angling NNE through the SE quadrant.
RAIL_P0, RAIL_P1, RAIL_HALF_W = (610.0, -1950.0), (1000.0, -200.0), 40.0
WATER_P0, WATER_P1, WATER_HALF_W = (-1400.0, -1120.0), (250.0, -1330.0), 25.0

TOMB_RING = [(740, -300), (1460, -300), (1500, -260), (1500, 460),
             (1460, 500), (740, 500), (700, 460), (700, -260)]
NURSERY_RING = [(690, 600), (1310, 600), (1350, 640), (1350, 1160),
                (1310, 1200), (690, 1200), (650, 1160), (650, 640)]

LANDMARKS = [
    ("Hazrat Nizamuddin Dargah", "mosque", (-650, 60)),
    ("Dargah Bazar", "market", (-600, -30)),
    ("Chausath Khamba", "monument", (-350, -150)),
    ("Humayun's Tomb", "monument", (1100, 100)),
    ("Sunder Nursery", "park", (1000, 880)),
    ("Hazrat Nizamuddin Railway Station", "rail", (935, -885)),
    ("Nizamuddin Polyclinic", "hospital", (350, 80)),
]

BASTI_ROW_NAMES = {0: ("Ghalib Road", "residential"),
                   -2: ("Musafir Khana Road", "residential"),
                   2: ("Baoli Gate Lane", "lane"),
                   4: ("Barakhamba Lane", "lane"),
                   -4: ("Sabz Burj Lane", "lane")}
BASTI_COL_NAMES = {0: ("Dargah Bazar Lane", "lane"),
                   -3: ("Kalan Masjid Lane", "lane"),
                   2: ("Chausath Khamba Lane", "lane")}

# Buildings: grid center of the basti (matches _basti), and the clearance
# every footprint corner keeps from every road centerline — a margin over
# the 3.5 m contract the tests enforce, so 6-decimal rounding can't nick it.
BASTI_CX, BASTI_CY = -650.0, 60.0
BUILDING_CLEAR_M = 4.0


def _band_ring(p0, p1, half_w):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    n = math.hypot(dx, dy)
    nx, ny = -dy / n * half_w, dx / n * half_w
    return [(p0[0] + nx, p0[1] + ny), (p0[0] - nx, p0[1] - ny),
            (p1[0] - nx, p1[1] - ny), (p1[0] + nx, p1[1] + ny)]


def _basti(net: Net, rng: random.Random):
    """Dense irregular old quarter: a jittered, rotated grid of short lanes
    with a ragged circular edge. Returns (node-index map, edge roads, the
    (i,j) node grid keys kept) for the drop/convert/footway passes."""
    cx, cy, sp, half = -650.0, 60.0, 85.0, 6
    cos_t, sin_t = math.cos(math.radians(15)), math.sin(math.radians(15))
    ids: dict[tuple[int, int], int] = {}
    for i in range(-half, half + 1):
        for j in range(-half, half + 1):
            ragged = 500 * (0.82 + 0.33 * rng.random())
            x = i * sp + rng.uniform(-20, 20)
            y = j * sp + rng.uniform(-20, 20)
            if math.hypot(i, j) * sp > ragged:
                continue
            ids[(i, j)] = net.node(cx + x * cos_t - y * sin_t,
                                   cy + x * sin_t + y * cos_t)
    edges = []
    for (i, j), a in ids.items():
        for di, dj in ((1, 0), (0, 1)):
            b = ids.get((i + di, j + dj))
            if b is None:
                continue
            name, cls = (BASTI_ROW_NAMES if dj == 0 else
                         BASTI_COL_NAMES).get(j if dj == 0 else i, (None, "lane"))
            edges.append(net.road([a, b], cls, name))
    return ids, edges, half


def _nearest(net: Net, ids: dict, tx: float, ty: float) -> int:
    return min(ids.values(),
               key=lambda n: math.hypot(net.meters[n][0] - tx,
                                        net.meters[n][1] - ty))


def _colony(net: Net):
    """Nizamuddin East: a calm planned residential grid, rotated to run
    parallel to the rail corridor. Returns (row roads, key junction ids)."""
    cx, cy = 1360.0, -890.0
    cos_t, sin_t = math.cos(math.radians(12.5)), math.sin(math.radians(12.5))
    xs = [1150, 1290, 1430, 1570]
    ys = [-540, -680, -820, -960, -1100, -1240]

    def pt(xb, yb):
        dx, dy = xb - cx, yb - cy
        return (cx + dx * cos_t - dy * sin_t, cy + dx * sin_t + dy * cos_t)

    ids = {(ci, ri): net.node(*pt(x, y))
           for ci, x in enumerate(xs) for ri, y in enumerate(ys)}
    row_names = ["A Block Road", "B Block Road", "C Block Road",
                 "D Block Road", "E Block Road", "F Block Road"]
    col_names = [None, "Community Centre Road",
                 "Nizamuddin East Market Road", None]
    for ri, name in enumerate(row_names):
        net.road([ids[(ci, ri)] for ci in range(len(xs))], "residential", name)
    for ci, name in enumerate(col_names):
        net.road([ids[(ci, ri)] for ri in range(len(ys))], "residential", name)
    return ids


def _build() -> Net:
    rng = random.Random(SEED)
    net = Net()

    # Arteries first: their vertices become the junctions everything joins.
    net.road(MATHURA, "primary", "Mathura Road")
    net.road(LODHI, "secondary", "Lodhi Road")
    net.road(WEST_MARG, "secondary", "Nizamuddin West Marg")

    colony = _colony(net)
    nw, sw = colony[(0, 0)], colony[(0, 5)]
    station_node = colony[(0, 2)]
    # The two designated rail crossings (an underpass by the station and
    # the old Barapullah bridge) — the only roads that touch the band.
    net.road([(363, -380), (700, -390), (930, -420), nw],
             "secondary", "Nizamuddin East Marg")
    net.road([(457, -1350), (800, -1320), sw], "secondary", "Old Barapullah Road")
    net.road([station_node, (945, -860)], "residential", "Station Road")
    net.road([(180, 600), (640, 620)], "residential", "Sunder Nursery Gate Road")

    basti_ids, basti_edges, half = _basti(net, rng)
    # Stitch the basti to the arteries at four compass points.
    net.road([net.node(-500, 1060), _nearest(net, basti_ids, -480, 520)],
             "residential", "Nizamuddin Basti Road")
    net.road([net.node(300, 50), _nearest(net, basti_ids, -160, 60)],
             "residential", "Dargah Approach Road")
    net.road([net.node(380, -500), _nearest(net, basti_ids, -160, -380)],
             "residential", None)
    net.road([net.node(-1220, 50), _nearest(net, basti_ids, -1080, 80)],
             "residential", None)
    net.road([net.node(-750, -830), _nearest(net, basti_ids, -680, -380)],
             "residential", None)

    # Footway texture: cut-through diagonals and dead-end gali spurs. These
    # go in BEFORE the drop pass so a drop that would strand one of their
    # anchor nodes fails the connectivity check instead of orphaning it.
    for i in range(-half, half):
        for j in range(-half, half):
            corners = [basti_ids.get(k) for k in
                       ((i, j), (i + 1, j), (i, j + 1), (i + 1, j + 1))]
            roll = rng.random()
            if None in corners:
                continue
            if roll < 0.22:
                a, b = (corners[0], corners[3]) if rng.random() < 0.5 else \
                       (corners[1], corners[2])
                net.road([a, b], "footway", None)
            elif roll < 0.34:
                cxm = (net.meters[corners[0]][0] + net.meters[corners[3]][0]) / 2
                cym = (net.meters[corners[0]][1] + net.meters[corners[3]][1]) / 2
                spur = net.node(cxm + rng.uniform(-8, 8), cym + rng.uniform(-8, 8))
                net.road([rng.choice(corners), spur], "footway", None)

    # Pedestrian loop around Humayun's Tomb, tied in at both ends.
    net.road([net.node(700, -390), (660, -300), (620, 100), (680, 470),
              (900, 560), (1200, 570), (1480, 520), (1560, 200),
              (1550, -150), (1380, -330), (1200, -350), nw], "footway", None)

    # Ragged-ify the basti: drop ~15% of edges, but never break the graph.
    candidates = list(basti_edges)
    rng.shuffle(candidates)
    quota = int(0.15 * len(basti_edges))
    dropped = []
    for r in candidates:
        if len(dropped) >= quota:
            break
        trial = dropped + [r]
        if net.all_connected(skip=trial) and net.scooter_connected(skip=trial):
            dropped.append(r)
    net.roads = [r for r in net.roads if id(r) not in {id(d) for d in dropped}]
    kept = {id(r) for r in net.roads}
    basti_edges = [r for r in basti_edges if id(r) in kept]

    # Demote ~12% of unnamed lanes to footways (too narrow for a scooter),
    # only where the scooter graph stays whole.
    lanes = [r for r in basti_edges if r["cls"] == "lane" and not r["name"]]
    rng.shuffle(lanes)
    quota = int(0.12 * len(basti_edges))
    for r in lanes:
        if quota <= 0:
            break
        if net.scooter_connected(skip=[r]):
            r["cls"] = "footway"
            quota -= 1
    return net


def _seg_dist(px, py, ax, ay, bx, by) -> float:
    """Metre distance from point (px, py) to segment (ax, ay)-(bx, by)."""
    dx, dy = bx - ax, by - ay
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def _in_ring(x, y, ring) -> bool:
    """Ray-cast point-in-polygon over a metre-space ring (unclosed)."""
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def _buildings(net: Net) -> list[list[tuple[float, float]]]:
    """Building footprints: quads with 6-16 m sides, jitter-rotated roughly
    parallel to their street and set 5-9 m off residential/lane centerlines
    — dense in the basti, sparser elsewhere (Nizamuddin East's calm blocks).
    Every corner keeps BUILDING_CLEAR_M from every road centerline, stays
    out of park/water/rail polygons and inside the zone; candidates that
    fail are simply dropped, so the fixed-seed draw stays deterministic."""
    rng = random.Random(SEED + 1)
    segs = []                       # (bbox x0, y0, x1, y1, ax, ay, bx, by)
    for r in net.roads:
        for a, b in zip(r["nodes"], r["nodes"][1:]):
            (ax, ay), (bx, by) = net.meters[a], net.meters[b]
            segs.append((min(ax, bx), min(ay, by), max(ax, bx), max(ay, by),
                         ax, ay, bx, by))
    avoid = [TOMB_RING, NURSERY_RING,
             _band_ring(RAIL_P0, RAIL_P1, RAIL_HALF_W),
             _band_ring(WATER_P0, WATER_P1, WATER_HALF_W)]

    def clear(x: float, y: float) -> bool:
        if math.hypot(x, y) > 2050 or any(_in_ring(x, y, r) for r in avoid):
            return False
        m = BUILDING_CLEAR_M
        for x0, y0, x1, y1, ax, ay, bx, by in segs:
            if (x0 - m < x < x1 + m and y0 - m < y < y1 + m
                    and _seg_dist(x, y, ax, ay, bx, by) < m):
                return False
        return True

    quads: list[list[tuple[float, float]]] = []
    placed: list[tuple[float, float, float]] = []    # (cx, cy, half-diagonal)
    for r in net.roads:
        if r["cls"] not in ("residential", "lane"):
            continue
        for a, b in zip(r["nodes"], r["nodes"][1:]):
            (ax, ay), (bx, by) = net.meters[a], net.meters[b]
            length = math.hypot(bx - ax, by - ay)
            if length < 24:
                continue
            ux, uy = (bx - ax) / length, (by - ay) / length
            basti = math.hypot((ax + bx) / 2 - BASTI_CX,
                               (ay + by) / 2 - BASTI_CY) < 620
            step = 30.0 if basti else 46.0
            p_build = 0.58 if basti else 0.4
            t = step * rng.uniform(0.35, 0.65)
            while t < length - 8:
                px, py = ax + ux * t, ay + uy * t
                for side in (1, -1):
                    if rng.random() > p_build:
                        continue
                    w, d = rng.uniform(6, 16), rng.uniform(6, 13)
                    off = side * (rng.uniform(5, 9) + d / 2)
                    rot = math.radians(rng.uniform(-9, 9))
                    fx = ux * math.cos(rot) - uy * math.sin(rot)
                    fy = ux * math.sin(rot) + uy * math.cos(rot)
                    cx, cy = px - fy * off, py + fx * off
                    hw, hd = w / 2, d / 2
                    quad = [(cx + fx * hw - fy * hd, cy + fy * hw + fx * hd),
                            (cx - fx * hw - fy * hd, cy - fy * hw + fx * hd),
                            (cx - fx * hw + fy * hd, cy - fy * hw - fx * hd),
                            (cx + fx * hw + fy * hd, cy + fy * hw - fx * hd)]
                    rad = math.hypot(hw, hd)
                    if (all(clear(x, y) for x, y in quad)
                            and all(math.hypot(cx - qx, cy - qy)
                                    >= 0.75 * (rad + qr)
                                    for qx, qy, qr in placed)):
                        quads.append(quad)
                        placed.append((cx, cy, rad))
                t += step * rng.uniform(0.85, 1.25)
    return quads


def generate() -> dict:
    net = _build()
    features = []
    for r in net.roads:
        props = {"kind": "road", "class": r["cls"]}
        if r["name"]:
            props["name"] = r["name"]
        features.append({
            "type": "Feature", "properties": props,
            "geometry": {"type": "LineString",
                         "coordinates": [list(net.coords[n]) for n in r["nodes"]]}})

    def area(kind, ring_m, name=None):
        props = {"kind": kind}
        if name:
            props["name"] = name
        ring = [list(_lnglat(*p)) for p in ring_m]
        ring.append(ring[0])
        features.append({"type": "Feature", "properties": props,
                         "geometry": {"type": "Polygon", "coordinates": [ring]}})

    area("park", TOMB_RING, "Humayun's Tomb")
    area("park", NURSERY_RING, "Sunder Nursery")
    area("rail", _band_ring(RAIL_P0, RAIL_P1, RAIL_HALF_W))
    area("water", _band_ring(WATER_P0, WATER_P1, WATER_HALF_W), "Barapullah Drain")

    for quad in _buildings(net):
        ring = [list(_lnglat(*p)) for p in quad]
        ring.append(ring[0])
        features.append({"type": "Feature", "properties": {"kind": "building"},
                         "geometry": {"type": "Polygon", "coordinates": [ring]}})

    for name, icon, (x, y) in LANDMARKS:
        features.append({
            "type": "Feature",
            "properties": {"kind": "landmark", "name": name, "icon": icon},
            "geometry": {"type": "Point", "coordinates": list(_lnglat(x, y))}})

    fc = {"type": "FeatureCollection", "note": NOTE, "features": features}
    _check(fc, net)
    return fc


def _check(fc: dict, net: Net) -> None:
    roads = [f for f in fc["features"] if f["properties"]["kind"] == "road"]
    assert 150 <= len(roads) <= 350, len(roads)
    assert net.all_connected(), "road graph is not one component"
    assert net.scooter_connected(), "scooter graph is not one component"
    names = {f["properties"].get("name") for f in roads} - {None}
    assert len(names) >= 8, names
    bldgs = [f for f in fc["features"] if f["properties"]["kind"] == "building"]
    assert 250 <= len(bldgs) <= 500, len(bldgs)
    for f in fc["features"]:
        g = f["geometry"]
        pts = ([g["coordinates"]] if g["type"] == "Point"
               else g["coordinates"] if g["type"] == "LineString"
               else g["coordinates"][0])
        for lng, lat in pts:
            assert geo.haversine_m(CLAT, CLNG, lat, lng) <= 2100, (lng, lat)


def render(fc: dict) -> str:
    lines = ",\n".join(json.dumps(f, ensure_ascii=False) for f in fc["features"])
    head = json.dumps({"type": fc["type"], "note": fc["note"]}, ensure_ascii=False)
    return head[:-1] + ', "features": [\n' + lines + "\n]}\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    fc = generate()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(fc), encoding="utf-8")
    roads = [f for f in fc["features"] if f["properties"]["kind"] == "road"]
    named = sum(1 for f in roads if f["properties"].get("name"))
    bldgs = sum(1 for f in fc["features"]
                if f["properties"]["kind"] == "building")
    print(f"wrote {args.out} — {len(fc['features'])} features, "
          f"{len(roads)} roads ({named} named), {bldgs} buildings, "
          f"{args.out.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
