"""Generate pukaar/data/demo_city.geojson — the wider city around the pilot zone.

The hand-built pilot zone (pukaar/data/demo_zone.geojson) is ~1.6 km across.
Zoom out past it and, until this file existed, there was nothing: the founder
panned into a void. This script procedurally builds a plausible surrounding
city — arterials, ring roads, a secondary lattice, residential blocks, lanes,
building footprints, parks, a river, canals and rail — out to +/-10 km, in the
SAME FeatureCollection schema basemap.js already renders.

Two rules shape everything:

  1. Never overdraw the pilot zone — but never leave a moat around it either.
     The keep-out is not a circle: it is a raster mask of where the zone
     ACTUALLY has streets (every zone road vertex, dilated by ~150 m) plus
     its parks, water and rail. City streets are clipped out of that mask,
     so they fill right up to the hand-built network and also fill the empty
     pockets inside the zone's own rim instead of stopping short of it.
  2. Meet it honestly at the seam. The zone's arterials (Mathura Road, Lodhi
     Road, the Barapullah drain, the rail corridor, the east margs) are
     CONTINUED outward from their real end coordinates, and every clipped
     stub that lands near a zone road vertex is snapped onto it, so city
     streets join the zone's streets instead of dead-ending beside them.

This is invented geometry with invented names, not a map of anywhere. The
FeatureCollection note and the on-map attribution both say so, and no name
here is a claim about a real locality.

The router never reads this file — only demo_zone.geojson feeds the road
graph — so riders still travel exclusively on the hand-built pilot streets.

Deterministic: a fixed seed drives every jitter, so re-running reproduces the
committed file byte-for-byte.

Usage: python tools/make_city_surrounds.py [--out PATH]
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

SEED = 20260809
CLAT, CLNG = 28.5933, 77.2507
R_CITY = 10000.0        # half-extent of generated coverage, metres
R_RESIDENTIAL = 5600.0  # in-block streets only where a zoomed-in camera can be
R_LANE = 3000.0
R_BUILDING = 3300.0
GRID = 760.0            # street lattice spacing
ARTERIAL_EVERY = 3      # every Nth lattice line is a secondary, the rest minor

# Keep-out raster: cells this big, marked wherever the pilot zone already has
# a street within MASK_PAD metres. A circle would leave a visible moat around
# the zone's sparse rim; this hugs the real network.
MASK_CELL = 50.0
MASK_PAD = 150.0

NOTE = ("Procedurally generated demo surroundings for the Wayside pilot zone "
        "— invented streets, invented names, NOT surveyed map data and not a "
        "depiction of any real locality. Only demo_zone.geojson feeds the "
        "router; this file is basemap scenery. Swap in real OSM data via "
        "tools/fetch_real_roads.py.")

ROOT = Path(__file__).resolve().parents[1]
ZONE = ROOT / "pukaar" / "data" / "demo_zone.geojson"
OUT = ROOT / "pukaar" / "data" / "demo_city.geojson"


def _lnglat(x: float, y: float) -> tuple[float, float]:
    """Local metres (east, north of zone centre) -> rounded [lng, lat]."""
    lat, lng = geo.offset_m(CLAT, CLNG, y, x)
    return (round(lng, 6), round(lat, 6))


def _metres(lng: float, lat: float) -> tuple[float, float]:
    kx = 111320 * math.cos(math.radians(CLAT))
    return ((lng - CLNG) * kx, (lat - CLAT) * 111320)


# ------------------------------------------------------------- geometry --
def _pip(pt, ring) -> bool:
    """Point in polygon ring (metres), ray casting."""
    x, y = pt
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def _smooth(pts, per: bool = False, passes: int = 2):
    """Chaikin-ish corner rounding so generated arcs read as roads, not wire."""
    out = list(pts)
    for _ in range(passes):
        nxt = [] if per else [out[0]]
        rng_ = range(len(out)) if per else range(len(out) - 1)
        for i in rng_:
            a, b = out[i], out[(i + 1) % len(out)]
            nxt.append((a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25))
            nxt.append((a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75))
        if not per:
            nxt.append(out[-1])
        out = nxt
    return out


def _resample(pts, step: float):
    """Thin a polyline to roughly one vertex per `step` metres (keeps ends)."""
    if len(pts) < 3:
        return list(pts)
    out = [pts[0]]
    acc = 0.0
    for i in range(1, len(pts) - 1):
        acc += math.dist(pts[i], pts[i - 1])
        if acc >= step:
            out.append(pts[i])
            acc = 0.0
    out.append(pts[-1])
    return out


class City:
    def __init__(self) -> None:
        self.rng = random.Random(SEED)
        self.feats: list[dict] = []
        self.blockers: list[list[tuple[float, float]]] = []   # water + parks
        self.water: list[list[tuple[float, float]]] = []
        self.roadlines: list[tuple[list, str]] = []           # (pts_m, cls) for buildings
        self.zone_pts: list[tuple[float, float]] = []         # zone road vertices, metres
        self.mask: set[tuple[int, int]] = set()               # pilot-zone keep-out raster

    # ------------------------------------------------------ keep-out --
    def load_zone(self, path: Path) -> None:
        """Read the hand-built pilot zone and build the keep-out mask from
        what it actually contains: its road vertices (dilated), and its
        parks / water / rail as hard blockers."""
        if not path.is_file():
            return
        gj = json.loads(path.read_text(encoding="utf-8"))
        pad = int(MASK_PAD / MASK_CELL) + 1
        for f in gj["features"]:
            kind = f["properties"].get("kind")
            g = f["geometry"]
            if kind == "road":
                for lng, lat in g["coordinates"]:
                    p = _metres(lng, lat)
                    self.zone_pts.append(p)
                    ci, cj = int(p[0] // MASK_CELL), int(p[1] // MASK_CELL)
                    for di in range(-pad, pad + 1):
                        for dj in range(-pad, pad + 1):
                            if math.hypot(di, dj) * MASK_CELL <= MASK_PAD:
                                self.mask.add((ci + di, cj + dj))
            elif kind in ("park", "water", "rail", "campus"):
                ring = [_metres(*c) for c in g["coordinates"][0]]
                self.blockers.append(ring)
                if kind == "water":
                    self.water.append(ring)

    def _in_zone(self, p) -> bool:
        return (int(p[0] // MASK_CELL), int(p[1] // MASK_CELL)) in self.mask

    # ---------------------------------------------------------- output --
    def poly(self, ring, kind: str, name: str | None = None) -> None:
        ring = [tuple(p) for p in ring]
        if ring[0] != ring[-1]:
            ring = ring + [ring[0]]
        props: dict = {"kind": kind}
        if name:
            props["name"] = name
        self.feats.append({
            "type": "Feature", "properties": props,
            "geometry": {"type": "Polygon",
                         "coordinates": [[list(_lnglat(*p)) for p in ring]]},
        })

    def area(self, ring, kind: str, name: str | None = None) -> None:
        """A park/water body: emitted AND registered as a road blocker."""
        self.poly(ring, kind, name)
        closed = [tuple(p) for p in ring]
        self.blockers.append(closed)
        if kind == "water":
            self.water.append(closed)

    def place(self, x: float, y: float, name: str, rank: int) -> None:
        self.feats.append({
            "type": "Feature",
            "properties": {"kind": "place", "name": name, "rank": rank},
            "geometry": {"type": "Point", "coordinates": list(_lnglat(x, y))},
        })

    # ----------------------------------------------------------- roads --
    def _blocked(self, p, bridge: bool) -> bool:
        if abs(p[0]) > R_CITY or abs(p[1]) > R_CITY:
            return True
        if self._in_zone(p):
            return True
        for ring in self.blockers:
            if bridge and ring in self.water:
                continue          # arterials bridge water, minor streets don't
            if _pip(p, ring):
                return True
        return False

    def road(self, pts, cls: str, name: str | None = None,
             bridge: bool = False) -> None:
        """Add a road, split around the keep-out disc, parks and (unless it
        bridges) water. Original vertices are kept; only the crossing points
        are inserted, so clipping costs almost no file size."""
        runs, cur = [], []
        prev = pts[0]
        prev_bad = self._blocked(prev, bridge)
        if not prev_bad:
            cur.append(prev)
        for nxt in pts[1:]:
            d = math.dist(prev, nxt)
            steps = max(1, int(d // 45))
            for k in range(1, steps + 1):
                t = k / steps
                p = (prev[0] + (nxt[0] - prev[0]) * t, prev[1] + (nxt[1] - prev[1]) * t)
                bad = self._blocked(p, bridge)
                if bad != prev_bad:
                    if bad:                       # leaving the drawable area
                        cur.append(p)
                        if len(cur) > 1:
                            runs.append(cur)
                        cur = []
                    else:                         # re-entering it
                        cur = [p]
                    prev_bad = bad
                elif not bad and k == steps:
                    cur.append(p)
            prev = nxt
        if len(cur) > 1:
            runs.append(cur)
        for run in runs:
            if _length(run) < 60:
                continue
            self._emit_road(_snap_ends(run, self.zone_pts), cls, name)

    def _emit_road(self, pts, cls: str, name: str | None) -> None:
        props: dict = {"kind": "road", "class": cls}
        if name:
            props["name"] = name
        self.feats.append({
            "type": "Feature", "properties": props,
            "geometry": {"type": "LineString",
                         "coordinates": [list(_lnglat(*p)) for p in pts]},
        })
        if cls in ("residential", "lane"):
            self.roadlines.append((pts, cls))


def _length(pts) -> float:
    return sum(math.dist(pts[i], pts[i - 1]) for i in range(1, len(pts)))


def _snap_ends(pts, zone_pts, radius: float = 200.0):
    """Pull a clipped stub onto the nearest pilot-zone road vertex, so city
    streets JOIN the hand-built ones instead of stopping short of them. Ends
    with no zone road nearby are left exactly where the clip put them."""
    if not zone_pts:
        return pts
    out = list(pts)
    for idx in (0, -1):
        p = out[idx]
        best, bd = None, radius
        for q in zone_pts:
            d = math.dist(p, q)
            if d < bd:
                best, bd = q, d
                if bd < 1.0:
                    break
        if best is not None:
            out[idx] = best
    return out


def _band(path, half_w: float):
    """A polyline thickened into a polygon ring (rivers, canals, rail)."""
    left, right = [], []
    for i, p in enumerate(path):
        a = path[max(0, i - 1)]
        b = path[min(len(path) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / n * half_w, dx / n * half_w
        left.append((p[0] + nx, p[1] + ny))
        right.append((p[0] - nx, p[1] - ny))
    return left + right[::-1]


def _blob(cx, cy, r, rng, wobble=0.32, n=22):
    """An irregular closed area — parks and lakes are never circles."""
    pts = []
    phase = [rng.uniform(0, 6.28) for _ in range(3)]
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1 + wobble * (0.55 * math.sin(2 * a + phase[0])
                          + 0.3 * math.sin(3 * a + phase[1])
                          + 0.15 * math.sin(5 * a + phase[2]))
        pts.append((cx + r * k * math.cos(a), cy + r * k * math.sin(a)))
    return _smooth(pts, per=True, passes=1)


# --------------------------------------------------------------- layout --
# Seam continuations, read off the pilot zone's own end coordinates.
MATHURA_N = [(-50, 1750), (-140, 2600), (-150, 3500), (-60, 4600),
             (40, 5900), (90, 7300), (60, 8800), (30, 10200)]
MATHURA_S = [(520, -2000), (600, -2900), (700, -4000), (760, -5200),
             (720, -6600), (640, -8000), (600, -10200)]
LODHI_W = [(-1650, 980), (-2500, 930), (-3500, 900), (-4700, 940),
           (-6100, 1010), (-7600, 1040), (-9000, 1000), (-10200, 960)]
EAST_MARG = [(1079, -594), (1900, -690), (2700, -760), (3600, -700),
             (4600, -620), (5600, -560)]
BARAPULLAH_E = [(1231, -1277), (2100, -1330), (3000, -1400), (4000, -1470),
                (5000, -1520), (6200, -1560)]

# Water: the zone's Barapullah drain, continued both ways, and a river to the
# east that everything drains into.
DRAIN_W = [(-1403, -1195), (-2300, -1120), (-3300, -1090), (-4400, -1140),
           (-5600, -1220), (-7000, -1260)]
DRAIN_E = [(253, -1330), (1200, -1420), (2200, -1500), (3300, -1560),
           (4300, -1600)]
RIVER = [(4700, 10200), (4500, 8200), (4300, 6300), (4450, 4400),
         (4800, 2600), (4900, 900), (4600, -800), (4300, -2500),
         (4400, -4300), (4800, -6200), (5000, -8200), (4900, -10200)]

# Rail: the zone corridor, carried north and south across the city.
RAIL_N = [(1000, -200), (1180, 900), (1400, 2100), (1750, 3400),
          (2100, 4900), (2300, 6600), (2350, 8400), (2300, 10200)]
RAIL_S = [(610, -1950), (500, -3100), (330, -4400), (120, -5900),
          (-60, -7500), (-160, -9200), (-180, -10200)]
RAIL_W = [(-10200, 3600), (-8200, 3500), (-6000, 3350), (-4000, 3150),
          (-2400, 2900), (-1300, 2650)]

RADIALS = [
    # (bearing degrees clockwise from north, name)
    (28, "Anjuman Marg"), (72, "Chandan Marg"), (118, "Roshan Road"),
    (163, "Firoz Marg"), (208, "Neelam Road"), (252, "Zafar Marg"),
    (296, "Salim Road"), (338, "Barkat Marg"),
]

PLACES_1 = [
    ("Anjuman Bagh", -3400, 3100), ("Chandan Sarai", 3300, 2700),
    ("Roshan Vihar", 3600, -3200), ("Firoz Kunj", -600, -4200),
    ("Neelam Nagar", -4300, -2600), ("Zafar Enclave", -6600, 1900),
    ("Salim Pur", 1400, 6300), ("Barkat Colony", 6600, 900),
    ("Purani Mandi", -2100, -6400), ("Meher Bagh", 6100, 4700),
    ("Sitara Kunj", -7300, -4600), ("Alam Nagar", 2600, -7600),
]
PLACES_2 = [
    ("Teen Pul", -2450, 1150), ("Sabzi Chowk", 2350, 350),
    ("Naya Sarai", -1950, -2350), ("Hari Bagh", 1750, 2500),
    ("Kot Kunj", -3900, 350), ("Baghicha", 2900, -1900),
    ("Chirag Vihar", -1250, 3450), ("Moti Enclave", -5100, 2350),
    ("Rangoli Colony", 5200, 3000), ("Dhobi Ghat", -3050, -4300),
    ("Sarai Khas", 4600, -5300), ("Pipal Chowk", -5900, -900),
    ("Amrit Kunj", 700, -3100), ("Nau Bagh", -1550, 5100),
    ("Gulmohar Vihar", 7400, -2600), ("Jamun Colony", -8100, 2900),
]


def build() -> dict:
    c = City()
    rng = c.rng

    # Read the pilot zone first: it defines the keep-out mask AND the
    # junction vertices that clipped stubs snap onto.
    c.load_zone(ZONE)

    # ---- water first: roads are clipped against it -------------------
    c.area(_band(_smooth(RIVER), 190), "water", "Purani Nadi")
    c.area(_band(_smooth(DRAIN_W), 28), "water", "Barapullah Drain")
    c.area(_band(_smooth(DRAIN_E), 34), "water", "Barapullah Drain")
    c.area(_blob(-4600, 4300, 720, rng), "water", "Moti Jheel")
    c.area(_blob(-3100, -5400, 560, rng), "water", "Purani Jheel")
    c.area(_blob(6900, 5600, 480, rng), "water")

    # ---- green ---------------------------------------------------------
    c.area(_blob(-6200, 600, 2100, rng, wobble=0.4, n=26), "park", "City Ridge Forest")
    c.area(_blob(3000, 5200, 1150, rng), "park", "Meher Bagh Park")
    c.area(_blob(-2400, -3600, 780, rng), "park", "Firoz Bagh")
    c.area(_blob(5900, -4400, 900, rng), "park", "Sarai Khas Park")
    c.area(_blob(-800, 6600, 950, rng), "park", "Nau Bagh Park")
    c.area(_blob(2200, -5600, 620, rng), "park")
    c.area(_blob(-5200, -7400, 1100, rng), "park")
    c.area(_blob(7900, 2400, 800, rng), "park")
    c.area(_blob(-1800, 2600, 420, rng), "park", "Teen Pul Garden")
    c.area(_blob(2600, 1500, 380, rng), "park")

    # ---- rail (drawn as bands, like the zone's corridor) --------------
    for path in (RAIL_N, RAIL_S, RAIL_W):
        c.poly(_band(_smooth(path), 38), "rail")

    # ---- arterials continuing the pilot zone --------------------------
    seam = [
        (MATHURA_N, "primary", "Mathura Road"), (MATHURA_S, "primary", "Mathura Road"),
        (LODHI_W, "primary", "Lodhi Road"),
        (EAST_MARG, "secondary", "Nizamuddin East Marg"),
        (BARAPULLAH_E, "secondary", "Old Barapullah Road"),
    ]
    for path, cls, name in seam:
        c.road(_resample(_smooth(path), 260), cls, name, bridge=True)

    # ---- ring roads ----------------------------------------------------
    for radius, name in ((3450, "Ring Road"), (7650, "Outer Ring Road")):
        pts = []
        for i in range(120):
            a = 2 * math.pi * i / 120
            k = radius * (1 + 0.07 * math.sin(3 * a + 0.8) + 0.04 * math.sin(5 * a))
            pts.append((k * math.sin(a), k * math.cos(a)))
        pts.append(pts[0])
        c.road(_resample(pts, 240), "primary", name, bridge=True)

    # ---- radial arterials ---------------------------------------------
    for bearing, name in RADIALS:
        a = math.radians(bearing)
        pts = []
        for r in range(1200, 14000, 340):
            drift = 260 * math.sin(r / 3300.0 + bearing)
            aa = a + drift / max(r, 1)
            pts.append((r * math.sin(aa), r * math.cos(aa)))
        c.road(_resample(_smooth(pts), 300), "primary", name, bridge=True)

    # ---- the street lattice --------------------------------------------
    # A warped grid, not graph paper: each line drifts on its own phase, so
    # blocks come out as slightly irregular quadrilaterals. Only every third
    # line is an arterial — that hierarchy is what stops a zoomed-out view
    # reading as yellow squared paper instead of a city.
    n = int(R_CITY / GRID)
    for i in range(-n, n + 1):
        base = i * GRID
        ph = rng.uniform(0, 6.28)
        amp = rng.uniform(35, 105)
        cls = "secondary" if i % ARTERIAL_EVERY == 0 else "residential"
        horiz = [(t, base + amp * math.sin(t / 2600.0 + ph))
                 for t in range(-int(R_CITY), int(R_CITY) + 1, 300)]
        vert = [(base + amp * math.sin(t / 2400.0 + ph + 1.7), t)
                for t in range(-int(R_CITY), int(R_CITY) + 1, 300)]
        for pts in (horiz, vert):
            c.road(_resample(pts, 300), cls)

    # ---- neighbourhood lanes inside each lattice block ------------------
    # Every lane spans its whole block, so it lands ON the lattice lines at
    # both ends: the result reads as a connected little street grid rather
    # than the field of floating dashes that free-standing stubs produce.
    m = int(R_RESIDENTIAL / GRID)
    for i in range(-m, m):
        for j in range(-m, m):
            cx, cy = (i + 0.5) * GRID, (j + 0.5) * GRID
            if math.hypot(cx, cy) > R_RESIDENTIAL:
                continue
            near = math.hypot(cx, cy) < R_LANE     # denser close to the zone
            rows = (0.32, 0.66) if near or rng.random() < 0.6 else (0.5,)
            cols = (0.34, 0.68) if near else ((0.5,) if rng.random() < 0.7 else ())
            for f in rows:
                off = (j + f) * GRID + rng.uniform(-22, 22)
                c.road([(i * GRID - 12, off),
                        (i * GRID + GRID * 0.5, off + rng.uniform(-16, 16)),
                        ((i + 1) * GRID + 12, off)], "lane")
            for g in cols:
                off = (i + g) * GRID + rng.uniform(-22, 22)
                c.road([(off, j * GRID - 12),
                        (off + rng.uniform(-16, 16), j * GRID + GRID * 0.5),
                        (off, (j + 1) * GRID + 12)], "lane")

    # ---- building footprints along the minor streets -------------------
    _buildings(c, rng)

    # ---- place labels ---------------------------------------------------
    for name, x, y in PLACES_1:
        c.place(x, y, name, 1)
    for name, x, y in PLACES_2:
        c.place(x, y, name, 2)

    return {"type": "FeatureCollection", "note": NOTE, "features": c.feats}


def _buildings(c: City, rng: random.Random) -> None:
    """Small jittered quads set back from the minor streets, thinning with
    distance so the inner ring reads dense and the outskirts read suburban."""
    made = 0
    for pts, cls in c.roadlines:
        for i in range(1, len(pts)):
            a, b = pts[i - 1], pts[i]
            seg = math.dist(a, b)
            if seg < 40:
                continue
            dx, dy = (b[0] - a[0]) / seg, (b[1] - a[1]) / seg
            nx, ny = -dy, dx
            step = 34 if cls == "lane" else 46
            t = step * 0.6
            while t < seg - 12:
                mx, my = a[0] + dx * t, a[1] + dy * t
                r = math.hypot(mx, my)
                if r > R_BUILDING or c._in_zone((mx, my)):
                    t += step
                    continue
                # density falls off with distance from the pilot zone
                if rng.random() > max(0.16, 1.15 - r / R_BUILDING):
                    t += step
                    continue
                for side in (1, -1):
                    if rng.random() < 0.3:
                        continue
                    off = (11 if cls == "lane" else 14) + rng.uniform(0, 7)
                    w = rng.uniform(9, 17)
                    h = rng.uniform(9, 15)
                    ccx = mx + nx * off * side
                    ccy = my + ny * off * side
                    ring = []
                    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                        ring.append((ccx + dx * sx * w / 2 + nx * sy * h / 2,
                                     ccy + dy * sx * w / 2 + ny * sy * h / 2))
                    c.poly(ring, "building")
                    made += 1
                t += step + rng.uniform(-6, 10)
    print(f"  buildings: {made}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    fc = build()
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fc, separators=(",", ":")), encoding="utf-8")
    counts: dict[str, int] = {}
    verts = 0
    for f in fc["features"]:
        k = f["properties"].get("kind")
        if k == "road":
            k = "road/" + f["properties"]["class"]
        counts[k] = counts.get(k, 0) + 1
        g = f["geometry"]
        verts += (1 if g["type"] == "Point"
                  else len(g["coordinates"]) if g["type"] == "LineString"
                  else sum(len(r) for r in g["coordinates"]))
    print(f"wrote {path} — {len(fc['features'])} features, {verts} vertices, "
          f"{path.stat().st_size / 1024:.0f} KB")
    for k in sorted(counts):
        print(f"  {k:22s} {counts[k]}")


if __name__ == "__main__":
    main()
