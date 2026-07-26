import pytest

from pukaar import digipin, geo


def test_roundtrip_delhi():
    lat, lng = 28.5933, 77.2507
    code = digipin.encode(lat, lng)
    assert len(code.replace("-", "")) == 10
    assert code.count("-") == 2
    dlat, dlng = digipin.decode(code)
    assert geo.haversine_m(lat, lng, dlat, dlng) < 10  # level-10 cell ~3.8m


def test_roundtrip_grid_of_points():
    for lat in (8.1, 13.05, 19.9, 26.8, 34.2):
        for lng in (68.9, 72.8, 77.2, 88.3, 93.9):
            code = digipin.encode(lat, lng)
            dlat, dlng = digipin.decode(code)
            assert geo.haversine_m(lat, lng, dlat, dlng) < 10


def test_distinct_nearby_points_get_distinct_codes():
    a = digipin.encode(28.5933, 77.2507)
    b = digipin.encode(28.5943, 77.2517)  # ~140m away
    assert a != b


def test_out_of_bounds_rejected():
    with pytest.raises(ValueError):
        digipin.encode(51.5, -0.1)  # London


def test_bad_code_rejected():
    with pytest.raises(ValueError):
        digipin.decode("39J-49L")
    with pytest.raises(ValueError):
        digipin.decode("39J-49L-L8Z4")  # Z not in grid
