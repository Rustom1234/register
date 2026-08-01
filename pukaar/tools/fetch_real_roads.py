"""Fetch real OSM streets/parks/water/rail and write the demo-zone schema.

This is the swap-in-real-data path for the committed, representative
pukaar/data/demo_zone.geojson: run it ON YOUR OWN MACHINE (this repo's
sandbox blocks all network access, so it cannot run there) and point the
app at the output. It queries the Overpass API once, converts the result
to the exact FeatureCollection schema the demo expects — road LineStrings
with class primary/secondary/residential/lane/footway, park/water/rail
Polygons, landmark Points — and writes it with coordinates rounded to 6
decimal places so shared OSM nodes stay shared vertices.

Data © OpenStreetMap contributors, ODbL — keep the attribution if you
ship the output.

Usage:
    python tools/fetch_real_roads.py --lat 28.5933 --lng 77.2507 \
        --radius 1500 --out pukaar/data/demo_zone.geojson

The tag-mapping helpers (road_class, area_kind, landmark_icon) are pure
functions covered by tests/test_demo_zone.py; the network path is not
testable offline by design.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
TIMEOUT_S = 90

_ROAD_CLASS = {
    "motorway": "primary", "trunk": "primary", "primary": "primary",
    "secondary": "secondary", "tertiary": "secondary",
    "residential": "residential", "unclassified": "residential",
    "living_street": "residential",
    "service": "lane", "track": "lane",
    "footway": "footway", "path": "footway", "pedestrian": "footway",
    "steps": "footway", "bridleway": "footway",
}


def road_class(tags: dict | None) -> str | None:
    """OSM tags -> demo-zone road class, or None for non-roads.

    '_link' variants map with their parent (primary_link -> primary)."""
    hw = (tags or {}).get("highway", "")
    return _ROAD_CLASS.get(hw.removesuffix("_link"))


def area_kind(tags: dict | None) -> str | None:
    """OSM tags -> demo-zone area kind (park/water/rail/campus), or None."""
    t = tags or {}
    if t.get("leisure") in ("park", "garden", "nature_reserve"):
        return "park"
    if t.get("natural") == "water" or t.get("waterway") in ("riverbank", "dock") \
            or t.get("landuse") in ("reservoir", "basin"):
        return "water"
    if t.get("landuse") == "railway" or t.get("railway") in ("rail", "yard", "station_area"):
        return "rail"
    if t.get("amenity") in ("university", "college", "school") \
            or t.get("landuse") == "education":
        return "campus"
    return None


def landmark_icon(tags: dict | None) -> str | None:
    """OSM tags -> demo-zone landmark icon, or None to skip the node."""
    t = tags or {}
    if t.get("railway") == "station":
        return "rail"
    if t.get("historic") in ("monument", "tomb", "memorial", "fort", "archaeological_site"):
        return "monument"
    if t.get("amenity") == "place_of_worship" and t.get("religion") == "muslim":
        return "mosque"
    if t.get("amenity") in ("hospital", "clinic"):
        return "hospital"
    if t.get("amenity") == "marketplace":
        return "market"
    if t.get("leisure") in ("park", "garden"):
        return "park"
    return None


def _query(lat: float, lng: float, radius: int) -> str:
    around = f"(around:{radius},{lat},{lng})"
    return f"""[out:json][timeout:{TIMEOUT_S - 5}];
(
  way["highway"]{around};
  way["leisure"~"park|garden|nature_reserve"]{around};
  way["natural"="water"]{around};
  way["landuse"~"railway|reservoir|basin|education"]{around};
  way["railway"~"rail|yard|station_area"]{around};
  node["railway"="station"]{around};
  node["historic"]{around};
  node["amenity"~"place_of_worship|hospital|clinic|marketplace"]{around};
);
out tags geom;"""


def _fetch(query: str) -> dict:
    body = urllib.parse.urlencode({"data": query}).encode()
    last_err: Exception | None = None
    for attempt in (1, 2):                       # one retry, then give up
        try:
            req = urllib.request.Request(
                OVERPASS_URL, data=body,
                headers={"User-Agent": "pukaar-demo-zone/0.1"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return json.load(resp)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            if attempt == 1:
                print(f"overpass attempt 1 failed ({e}); retrying in 5s...",
                      file=sys.stderr)
                time.sleep(5)
    raise SystemExit(
        f"error: could not reach the Overpass API: {last_err}\n"
        "Check your network (this script cannot run inside the repo sandbox, "
        "which blocks all outbound traffic) or try again later — Overpass "
        "rate-limits busy periods.")


def _round_pts(geom: list[dict]) -> list[list[float]]:
    return [[round(p["lon"], 6), round(p["lat"], 6)] for p in geom]


def convert(elements: list[dict]) -> list[dict]:
    """Overpass 'out geom' elements -> demo-zone schema features."""
    features = []
    for el in elements:
        tags = el.get("tags", {})
        if el.get("type") == "way" and el.get("geometry"):
            pts = _round_pts(el["geometry"])
            cls = road_class(tags)
            kind = area_kind(tags)
            if cls is not None and len(pts) >= 2:
                props = {"kind": "road", "class": cls}
                if tags.get("name"):
                    props["name"] = tags["name"]
                features.append({"type": "Feature", "properties": props,
                                 "geometry": {"type": "LineString",
                                              "coordinates": pts}})
            elif kind is not None and len(pts) >= 4 and pts[0] == pts[-1]:
                props = {"kind": kind}
                if tags.get("name"):
                    props["name"] = tags["name"]
                features.append({"type": "Feature", "properties": props,
                                 "geometry": {"type": "Polygon",
                                              "coordinates": [pts]}})
        elif el.get("type") == "node":
            icon = landmark_icon(tags)
            if icon and tags.get("name"):
                features.append({
                    "type": "Feature",
                    "properties": {"kind": "landmark", "name": tags["name"],
                                   "icon": icon},
                    "geometry": {"type": "Point",
                                 "coordinates": [round(el["lon"], 6),
                                                 round(el["lat"], 6)]}})
    return features


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lat", type=float, default=28.5933)
    ap.add_argument("--lng", type=float, default=77.2507)
    ap.add_argument("--radius", type=int, default=1500,
                    help="metres around --lat/--lng (default 1500)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if not 50 <= args.radius <= 10_000:
        raise SystemExit("error: --radius must be 50..10000 metres")

    print(f"querying Overpass for {args.radius} m around "
          f"{args.lat},{args.lng} ...", file=sys.stderr)
    data = _fetch(_query(args.lat, args.lng, args.radius))
    features = convert(data.get("elements", []))
    if not features:
        raise SystemExit("error: Overpass returned no usable features — "
                         "check the coordinates and radius.")
    fc = {"type": "FeatureCollection",
          "note": ("Real OSM data © OpenStreetMap contributors (ODbL), "
                   "fetched by tools/fetch_real_roads.py."),
          "features": features}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
        f.write("\n")
    roads = sum(1 for f in features if f["properties"]["kind"] == "road")
    print(f"wrote {args.out} — {len(features)} features ({roads} roads)")


if __name__ == "__main__":
    main()
