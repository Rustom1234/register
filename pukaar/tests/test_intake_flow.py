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
    # stray taps stay silent while stopped…
    assert svc.wa_inbound("+91-902", "button", text="cat:food") == []
    assert svc.wa_inbound("+91-902", "location", lat=28.59, lng=77.25) == []
    # …but a fresh text re-opens the line, as S-STOP promises
    assert svc.wa_inbound("+91-902", "text", text="wapas hoon, madad chahiye") != []


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


def test_pinless_unknown_landmark_reaches_a_human(svc, clock):
    """NGO-ops audit: a witness whose landmark isn't in the vocabulary must
    never be asked "where?" forever and then lost — after two unanswered
    asks the words they typed become a landmark-only case for the
    coordinator's request-pin rail."""
    msgs = ["aadmi ghayal hai dargah ke paas chai ki dukaan ke saamne",
            "dargah ke paas chai ki dukaan", "bas wahi dukaan ke saamne"]
    for m in msgs:
        clock.advance(30)
        out = svc.wa_inbound("+919999000111", "text", m)
    # third turn moved past location instead of asking a third time
    assert "S-ASK-LOCATION" not in [b.string_id for b in out]
    clock.advance(30)
    svc.wa_inbound("+919999000111", "button", "fresh:10")
    case = svc.store.one("SELECT * FROM cases")
    assert case is not None and case["geo_conf"] == "landmark"
    assert "dargah" in (case["landmark_text"] or "")


def test_dedup_never_merges_across_categories(svc, clock):
    """A food report near an open medical case is a DIFFERENT person."""
    svc.wa_inbound("+911111", "text", "aadmi ghayal hai patti chahiye")
    svc.wa_inbound("+911111", "location", lat=28.5933, lng=77.2507)
    svc.wa_inbound("+911111", "button", "fresh:10")
    clock.advance(600)
    svc.wa_inbound("+912222", "text", "amma bhookhi hai wahin par")
    svc.wa_inbound("+912222", "location", lat=28.5935, lng=77.2508)
    svc.wa_inbound("+912222", "button", "fresh:10")
    cases = svc.store.query("SELECT * FROM cases ORDER BY created_at")
    assert len(cases) == 2, [c["category"] for c in cases]
    assert {c["category"] for c in cases} == {"medical", "food"}


def test_unvetted_responder_gets_no_offers(svc, clock):
    """Vetting is a gate, not a badge: pending vetting = no offers, no
    manual assignment, no accept."""
    svc.store.insert("responders", {
        "id": "resp_x", "partner_id": "partner_1", "display_name": "Naya",
        "medical": 1, "vetting": "pending", "active": 1})
    svc.positions["resp_x"] = (28.5933, 77.2507)
    svc.wa_inbound("+913333", "text", "aadmi ghayal hai patti chahiye")
    svc.wa_inbound("+913333", "location", lat=28.5933, lng=77.2507)
    svc.wa_inbound("+913333", "button", "fresh:10")
    clock.advance(5)
    svc.dispatch.tick()
    assert svc.store.query(
        "SELECT * FROM assignments WHERE responder_id='resp_x'") == []
    order = svc.store.one("SELECT * FROM orders")
    assert not svc.dispatch.manual_assign(order["id"], "resp_x")
