from pukaar import geo


def test_haversine_known_distance():
    # Nizamuddin to Humayun's Tomb ~= 1.1km-ish; sanity band
    d = geo.haversine_m(28.5933, 77.2507, 28.5933, 77.2607)
    assert 900 < d < 1100  # ~0.01 deg lng at this latitude


def test_cell_key_stable_and_neighbors_cover():
    lat, lng = 28.5933, 77.2507
    k = geo.cell_key(lat, lng)
    assert k == geo.cell_key(lat, lng)
    neigh = geo.neighbor_keys(lat, lng)
    assert k in neigh and len(neigh) == 9
    # a point ~100m away shares the 3x3 neighborhood
    lat2, lng2 = geo.offset_m(lat, lng, 100, 0)
    assert geo.cell_key(lat2, lng2) in neigh


def test_step_towards_arrives():
    lat, lng = 28.5933, 77.2507
    tlat, tlng = geo.offset_m(lat, lng, 50, 50)
    lat2, lng2 = geo.step_towards(lat, lng, tlat, tlng, 10_000)
    assert (lat2, lng2) == (tlat, tlng)
