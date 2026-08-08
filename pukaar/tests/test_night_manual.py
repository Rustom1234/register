"""Night-mode dispatch windows and coordinator manual assignment."""

from pukaar import geo


def _seed_responders(svc, positions):
    for i, (lat, lng) in enumerate(positions):
        rid = f"resp_{i+1}"
        svc.store.insert("responders", {"id": rid, "partner_id": "partner_1",
                                        "display_name": f"R{i+1}", "medical": 0,
                                        "vetting": "verified", "active": 1})
        svc.positions[rid] = (lat, lng)


def _report(svc, phone, lat, lng):
    svc.wa_inbound(phone, "text", text="aadmi ghayal hai khoon nikal raha")
    svc.wa_inbound(phone, "location", lat=lat, lng=lng)
    return svc.wa_inbound(phone, "button", text="fresh:10")


def test_window_boundaries(svc, clock, cfg):
    clock.t = cfg.dispatch_open_h * 3600
    assert svc.dispatch.in_dispatch_window()
    clock.t = cfg.dispatch_close_h * 3600
    assert not svc.dispatch.in_dispatch_window()
    clock.t = 2 * 3600
    assert not svc.dispatch.in_dispatch_window()


def test_night_report_holds_until_morning(svc, clock, cfg):
    base = (28.5933, 77.2507)
    _seed_responders(svc, [geo.offset_m(*base, 100, 0), geo.offset_m(*base, 200, 0)])
    clock.t = 23 * 3600                     # 23:00 — outside dispatch window
    replies = _report(svc, "+91-N1", *base)
    assert any(r.string_id == "S-EXPECT-NIGHT" for r in replies)

    svc.dispatch.tick()                     # night: no waves start
    order = svc.store.one("SELECT * FROM orders")
    assert order["status"] == "queued"

    clock.t = 86400 + 8 * 3600              # next day, 08:00
    svc.dispatch.tick()
    order = svc.store.one("SELECT * FROM orders")
    assert order["status"] == "offered"


def test_day_report_gets_same_day_string(svc, clock, cfg):
    base = (28.5933, 77.2507)
    _seed_responders(svc, [geo.offset_m(*base, 100, 0)])
    clock.t = 10 * 3600
    replies = _report(svc, "+91-N2", *base)
    assert any(r.string_id == "S-EXPECT" for r in replies)


def test_manual_assign_recovers_stuck_order(svc, clock, cfg):
    base = (28.5933, 77.2507)
    clock.t = 10 * 3600
    _report(svc, "+91-N3", *base)           # no responders seeded -> coordinator
    svc.dispatch.tick()
    order = svc.store.one("SELECT * FROM orders")
    assert order["status"] == "needs_coordinator"

    _seed_responders(svc, [geo.offset_m(*base, 150, 0)])
    assert svc.dispatch.manual_assign(order["id"], "resp_1", force=True)
    order = svc.store.one("SELECT * FROM orders")
    assert order["status"] == "accepted" and order["responder_id"] == "resp_1"
    asg = svc.store.one("SELECT * FROM assignments WHERE order_id=?", (order["id"],))
    assert asg["response"] == "accepted"


def test_manual_assign_rejects_bad_targets(svc, clock):
    assert not svc.dispatch.manual_assign("ord_missing", "resp_1")
