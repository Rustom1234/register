"""Dispatch engine: parallel waves, first-accept, timeouts, coordinator rung."""

from pukaar import geo


def _make_case_with_order(svc, priority="P2", lat=28.5933, lng=77.2507):
    case = {"id": "case_t1", "status": "routed", "category": "food", "category_conf": 1.0,
            "urgency": "medium", "cell": geo.cell_key(lat, lng), "lat": lat, "lng": lng,
            "geo_conf": "pin", "landmark_text": None, "freshness_min": 10, "detail": "",
            "merged_witnesses": 1, "created_at": svc.now(), "closed_at": None, "expires_at": None}
    svc.store.insert("cases", case)
    order = {"sku": "FOOD-1", "addons": [], "clinical_flag": False, "priority": priority,
             "instruction_ids": ["GI-1"], "confidence": 0.9, "needs_review": False,
             "created_by": "code:food", "kit": {}}
    return svc.dispatch.create_order(case, order, mac="x")


def _seed_responders(svc, positions):
    for i, (lat, lng) in enumerate(positions):
        rid = f"resp_{i+1}"
        svc.store.insert("responders", {"id": rid, "partner_id": "partner_1",
                                        "display_name": f"R{i+1}", "medical": 0,
                                        "vetting": "verified", "active": 1})
        svc.positions[rid] = (lat, lng)


def test_wave_offers_nearest_two_and_first_accept_locks(svc, clock):
    base = (28.5933, 77.2507)
    _seed_responders(svc, [geo.offset_m(*base, 100, 0), geo.offset_m(*base, 200, 0),
                           geo.offset_m(*base, 2000, 0)])
    order = _make_case_with_order(svc)
    svc.dispatch.tick()
    asgs = svc.store.query("SELECT * FROM assignments WHERE order_id=?", (order["id"],))
    assert {a["responder_id"] for a in asgs} == {"resp_1", "resp_2"}  # k=2, nearest

    assert svc.dispatch.respond(asgs[0]["id"], True)
    o = svc.store.one("SELECT * FROM orders WHERE id=?", (order["id"],))
    assert o["status"] == "accepted" and o["responder_id"] == asgs[0]["responder_id"]
    # sibling offer released
    other = svc.store.one("SELECT * FROM assignments WHERE id=?", (asgs[1]["id"],))
    assert other["response"] == "released"
    # a late accept on the released assignment cannot steal the order
    assert not svc.dispatch.respond(asgs[1]["id"], True)


def test_p1_offers_three(svc, clock):
    base = (28.5933, 77.2507)
    _seed_responders(svc, [geo.offset_m(*base, d, 0) for d in (100, 200, 300, 400)])
    order = _make_case_with_order(svc, priority="P1")
    svc.dispatch.tick()
    asgs = svc.store.query("SELECT * FROM assignments WHERE order_id=?", (order["id"],))
    assert len(asgs) == 3


def test_timeout_starts_next_wave_then_coordinator(svc, clock, cfg):
    base = (28.5933, 77.2507)
    _seed_responders(svc, [geo.offset_m(*base, 100, 0), geo.offset_m(*base, 200, 0)])
    order = _make_case_with_order(svc)
    svc.dispatch.tick()                       # wave 1 -> both offered
    clock.advance(cfg.offer_ttl_s + 1)
    svc.dispatch.tick()                       # wave 1 expired; wave 2 has no fresh candidates
    o = svc.store.one("SELECT * FROM orders WHERE id=?", (order["id"],))
    assert o["status"] == "needs_coordinator"


def test_declines_trigger_next_wave_with_new_candidates(svc, clock):
    base = (28.5933, 77.2507)
    _seed_responders(svc, [geo.offset_m(*base, d, 0) for d in (100, 200, 300, 400)])
    order = _make_case_with_order(svc)
    svc.dispatch.tick()
    wave1 = svc.store.query("SELECT * FROM assignments WHERE order_id=?", (order["id"],))
    for a in wave1:
        svc.dispatch.respond(a["id"], False)
    svc.dispatch.tick()                       # wave 2 -> next-nearest pair
    o = svc.store.one("SELECT * FROM orders WHERE id=?", (order["id"],))
    assert o["status"] == "offered" and o["wave"] == 2
    wave2 = svc.store.query(
        "SELECT * FROM assignments WHERE order_id=? AND responded_at IS NULL", (order["id"],))
    assert {a["responder_id"] for a in wave2} == {"resp_3", "resp_4"}


def test_outcome_closes_case(svc, clock):
    base = (28.5933, 77.2507)
    _seed_responders(svc, [geo.offset_m(*base, 100, 0)])
    order = _make_case_with_order(svc)
    svc.dispatch.tick()
    a = svc.store.one("SELECT * FROM assignments WHERE order_id=?", (order["id"],))
    svc.dispatch.respond(a["id"], True)
    svc.dispatch.arrived(order["id"])
    svc.dispatch.close(order["id"], "served")
    assert svc.store.one("SELECT * FROM cases WHERE id='case_t1'")["status"] == "closed"
    out = svc.store.one("SELECT * FROM outcomes WHERE case_id='case_t1'")
    assert out["served"] == 1 and out["found"] == 1


def test_escalation_keeps_case_open_until_completed(svc, clock):
    base = (28.5933, 77.2507)
    _seed_responders(svc, [geo.offset_m(*base, 100, 0)])
    order = _make_case_with_order(svc)
    svc.dispatch.tick()
    a = svc.store.one("SELECT * FROM assignments WHERE order_id=?", (order["id"],))
    svc.dispatch.respond(a["id"], True)
    svc.dispatch.arrived(order["id"])
    svc.dispatch.close(order["id"], "escalated")
    assert svc.store.one("SELECT * FROM cases WHERE id='case_t1'")["status"] == "escalated"
    svc.dispatch.escalation_complete(order["id"])
    case = svc.store.one("SELECT * FROM cases WHERE id='case_t1'")
    assert case["status"] == "closed"
    out = svc.store.one("SELECT * FROM outcomes WHERE case_id='case_t1'")
    assert out["escalation_completed_at"] is not None
