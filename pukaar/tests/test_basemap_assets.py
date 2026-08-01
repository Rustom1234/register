"""Static-asset checks for the Wayside basemap module.

basemap.js is a browser script, so pytest can't execute it; instead we
assert the shipped assets are present, self-contained (no external URLs
in code), and that the vendored glyph ranges are real PBFs, not saved
404 pages.
"""

from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "pukaar" / "static"
BASEMAP_JS = STATIC / "basemap.js"
GLYPH_DIR = STATIC / "vendor" / "glyphs" / "Noto Sans Regular"

EXPECTED_RANGES = ["0-255", "256-511", "512-767", "2304-2559", "2560-2815"]


def test_basemap_js_exists_and_nonempty():
    assert BASEMAP_JS.is_file()
    text = BASEMAP_JS.read_text(encoding="utf-8")
    assert len(text) > 1000
    assert "window.WaysideBasemap" in text
    assert "buildStyle" in text


def test_basemap_js_has_no_external_urls_outside_comments():
    in_block_comment = False
    for line in BASEMAP_JS.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if in_block_comment:
            if "*/" in stripped:
                in_block_comment = False
            continue
        if stripped.startswith("/*"):
            if "*/" not in stripped:
                in_block_comment = True
            continue
        code = line.split("//", 1)[0]
        assert "http://" not in code and "https://" not in code, (
            f"external URL in basemap.js code: {line!r}"
        )


def test_glyph_ranges_present_and_nontrivial():
    assert GLYPH_DIR.is_dir(), "glyph fontstack dir missing"
    for rng in EXPECTED_RANGES:
        pbf = GLYPH_DIR / f"{rng}.pbf"
        assert pbf.is_file(), f"missing glyph range {rng}"
        data = pbf.read_bytes()
        assert len(data) > 1024, f"glyph range {rng} suspiciously small"
        # A saved error page would start with markup, not protobuf bytes.
        assert not data.lstrip()[:1] in (b"<",), f"glyph range {rng} looks like HTML"


def test_basemap_eyeball_page_exists():
    page = STATIC / "basemap-test.html"
    assert page.is_file()
    text = page.read_text(encoding="utf-8")
    assert "basemap.js" in text
    assert "http://" not in text and "https://" not in text
