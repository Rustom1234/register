"""Geo helpers: haversine, coarse dedup cells, jitter for the sim.

Dedup uses a plain lat/lng grid keyed at ~cell_m meters (build plan §2:
no PostGIS/H3 dependency needed at pilot scale; the 3x3 neighborhood of a
~150m grid approximates H3 res-10 + kRing(1))."""

from __future__ import annotations

import math

EARTH_R = 6_371_000.0


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(a))


def cell_key(lat: float, lng: float, cell_m: float = 150.0) -> str:
    # The longitude step derives from the ROW's mid-latitude (not the
    # point's), so every point in a row shares one column grid — which
    # makes cell_bounds() an exact inverse for the heatmap.
    dlat = cell_m / 111_320.0
    i = math.floor(lat / dlat)
    dlng = _row_dlng(i, cell_m, dlat)
    return f"{i}:{math.floor(lng / dlng)}"


def _row_dlng(row: int, cell_m: float, dlat: float) -> float:
    lat_mid = (row + 0.5) * dlat
    return cell_m / (111_320.0 * max(0.2, math.cos(math.radians(lat_mid))))


def neighbor_keys(lat: float, lng: float, cell_m: float = 150.0) -> set[str]:
    dlat = cell_m / 111_320.0
    dlng = cell_m / (111_320.0 * max(0.2, math.cos(math.radians(lat))))
    keys = set()
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            keys.add(cell_key(lat + i * dlat, lng + j * dlng, cell_m))
    return keys


def cell_bounds(cell: str, cell_m: float = 150.0) -> tuple[float, float, float, float] | None:
    """(south, west, north, east) for a cell_key() key — the exact inverse
    of the row-quantized grid, used by the 90-day aggregate heatmap. None
    for non-grid keys ('unknown')."""
    try:
        i, j = (int(x) for x in cell.split(":"))
    except ValueError:
        return None
    dlat = cell_m / 111_320.0
    dlng = _row_dlng(i, cell_m, dlat)
    return (i * dlat, j * dlng, (i + 1) * dlat, (j + 1) * dlng)


def offset_m(lat: float, lng: float, north_m: float, east_m: float) -> tuple[float, float]:
    return (
        lat + north_m / 111_320.0,
        lng + east_m / (111_320.0 * max(0.2, math.cos(math.radians(lat)))),
    )


def step_towards(lat: float, lng: float, tlat: float, tlng: float, dist_m: float) -> tuple[float, float]:
    total = haversine_m(lat, lng, tlat, tlng)
    if total <= dist_m or total == 0:
        return tlat, tlng
    f = dist_m / total
    return lat + (tlat - lat) * f, lng + (tlng - lng) * f
