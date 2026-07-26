"""DIGIPIN encoder/decoder (India Post national geocode, launched May 2025).

Implements the published algorithm: the bounding box lat [2.5, 38.5] /
lon [63.5, 99.5] is subdivided 4x4 ten times; each level appends one
symbol from the labelling grid (row 0 = north). Display format groups
as XXX-XXX-XXXX. Cell size at level 10 is ~3.8m.

Honest limit: symbol-grid orientation is implemented from the public spec
as researched (build plan §2); round-trip correctness is fully tested here,
and cross-checking a handful of codes against India Post's official lookup
is a listed P1 task before any responder-facing use.
"""

from __future__ import annotations

_GRID = [
    ["F", "C", "9", "8"],
    ["J", "3", "2", "7"],
    ["K", "4", "5", "6"],
    ["L", "M", "P", "T"],
]
_POS = {ch: (r, c) for r, row in enumerate(_GRID) for c, ch in enumerate(row)}

LAT_MIN, LAT_MAX = 2.5, 38.5
LON_MIN, LON_MAX = 63.5, 99.5
LEVELS = 10


def encode(lat: float, lng: float) -> str:
    if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lng <= LON_MAX):
        raise ValueError("coordinates outside DIGIPIN bounds (India)")
    lat_lo, lat_hi = LAT_MIN, LAT_MAX
    lon_lo, lon_hi = LON_MIN, LON_MAX
    out: list[str] = []
    for _ in range(LEVELS):
        lat_step = (lat_hi - lat_lo) / 4
        lon_step = (lon_hi - lon_lo) / 4
        row = min(3, int((lat_hi - lat) / lat_step))       # 0 = northmost band
        col = min(3, int((lng - lon_lo) / lon_step))
        out.append(_GRID[row][col])
        lat_hi = lat_hi - row * lat_step
        lat_lo = lat_hi - lat_step
        lon_lo = lon_lo + col * lon_step
        lon_hi = lon_lo + lon_step
    s = "".join(out)
    return f"{s[:3]}-{s[3:6]}-{s[6:]}"


def decode(code: str) -> tuple[float, float]:
    """Return the center of the cell the code denotes."""
    s = code.replace("-", "").upper()
    if len(s) != LEVELS:
        raise ValueError("DIGIPIN must have 10 symbols")
    lat_lo, lat_hi = LAT_MIN, LAT_MAX
    lon_lo, lon_hi = LON_MIN, LON_MAX
    for ch in s:
        if ch not in _POS:
            raise ValueError(f"invalid DIGIPIN symbol: {ch}")
        row, col = _POS[ch]
        lat_step = (lat_hi - lat_lo) / 4
        lon_step = (lon_hi - lon_lo) / 4
        lat_hi = lat_hi - row * lat_step
        lat_lo = lat_hi - lat_step
        lon_lo = lon_lo + col * lon_step
        lon_hi = lon_lo + lon_step
    return (lat_lo + lat_hi) / 2, (lon_lo + lon_hi) / 2
