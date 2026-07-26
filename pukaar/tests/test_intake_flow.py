"""Intake conversation flow against the mock backend (the golden fixture)."""

from pukaar import geo


def _texts(replies):
    return [r.string_id for r in replies]


def test_full_flow_creates_case_and_order(svc, clock):
    phone = "+91-900"
    r1 = svc.wa_inbound(phone, "text", text="Bhaiya flyover ke neeche aadmi ghayal hai, patti mein khoon")
    assert "S-NOTICE" in _texts(r1)          # first-contact notice
    assert "S-ASK-LOCATION" in _texts(r1)    # location is the next missing slot

    lat, lng = 28.5933, 77.2507
    r2 = svc.wa_inbound(phone, "location", lat=lat, lng=lng)
    # category was already extracted (medical) -> extras ask
    assert "S-ASK-EXTRA" in _texts(r2)

    r3 = svc.wa_inbound(phone, "button", text="fresh:10")
    assert "S-EXPECT" in _texts(r3)

    cases = svc.store.query("SELECT * FROM cases")
    assert len(cases) == 1
    case = cases[0]
    assert case["category"] == "medical"
    assert case["status"] == "routed"
    orders = svc.store.query("SELECT * FROM orders")
    assert len(orders) == 1
    assert orders[0]["sku"] == "MED-1"
    assert orders[0]["clinical_flag"] == 1   # conservative default held


def test_emergency_gate_short_circuits(svc):
    replies = svc.wa_inbound("+91-901", "text", text="aadmi behosh pada hai!!")
    ids = _texts(replies)
    assert ids == ["S-112"]                  # no notice, no questions, no model path
    assert svc.store.query("SELECT * FROM cases") == []


def test_stop_opts_out(svc):
    svc.wa_inbound("+91-902", "text", text="hello")
    replies = svc.wa_inbound("+91-902", "text", text="STOP")
    assert _texts(replies) == ["S-STOP"]
    assert svc.wa_inbound("+91-902", "text", text="anything") == []


def test_category_buttons_when_ambiguous(svc):
    phone = "+91-903"
    svc.wa_inbound(phone, "text", text="ek aadmi hai yahan")  # no category signal
    r = svc.wa_inbound(phone, "location", lat=28.593, lng=77.251)
    assert "S-ASK-CATEGORY" in _texts(r)
    r2 = svc.wa_inbound(phone, "button", text="cat:food")
    assert "S-ASK-EXTRA" in _texts(r2)
    r3 = svc.wa_inbound(phone, "button", text="fresh:60")
    assert "S-EXPECT" in _texts(r3)
    assert svc.store.query("SELECT * FROM cases")[0]["category"] == "food"


def test_duplicate_reports_merge(svc):
    lat, lng = 28.5933, 77.2507
    for i, jitter in enumerate((0.0, 0.0004)):
        phone = f"+91-91{i}"
        svc.wa_inbound(phone, "text", text="aadmi ghayal hai khoon nikal raha")
        svc.wa_inbound(phone, "location", lat=lat + jitter, lng=lng + jitter)
        svc.wa_inbound(phone, "button", text="fresh:10")
    cases = svc.store.query("SELECT * FROM cases")
    assert len(cases) == 1
    assert cases[0]["merged_witnesses"] == 2
    assert len(svc.store.query("SELECT * FROM orders")) == 1


def test_far_reports_do_not_merge(svc):
    lat, lng = 28.5933, 77.2507
    lat2, lng2 = geo.offset_m(lat, lng, 900, 900)
    for i, (la, ln) in enumerate(((lat, lng), (lat2, lng2))):
        phone = f"+91-92{i}"
        svc.wa_inbound(phone, "text", text="aadmi ghayal hai")
        svc.wa_inbound(phone, "location", lat=la, lng=ln)
        svc.wa_inbound(phone, "button", text="fresh:10")
    assert len(svc.store.query("SELECT * FROM cases")) == 2
