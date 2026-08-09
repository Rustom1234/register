"""Calm demo mode: the founder-driven board.

`python -m pukaar` boots calm (see __main__): riders exist in the roster
but are off duty and off the map, nothing moves without a job, and the sim
never files its own witness reports. A rider joins by tapping "on duty"
in the rider app (POST /api/manual -> sim.set_duty), a human files a case,
the offer goes only to on-duty riders, and the winner drives current
position -> depot (kit pickup) -> pin along the road graph.
"""

from pukaar.config import Config
from pukaar.db import Store
from pukaar.service import PukaarService
from pukaar.sim import Sim


def _mk(ambient: bool = False, seed: int = 42):
    cfg = Config()
    cfg.backend = "mock"
    cfg.sim_ambient = ambient
    holder = {}
    svc = PukaarService(cfg, Store(":memory:"), now_fn=lambda: holder["sim"].sim_now)
    sim = Sim(svc, cfg, seed=seed)
    holder["sim"] = sim
    return cfg, svc, sim


def _run(sim, sim_seconds, step=5.0):
    t = 0.0
    while t < sim_seconds:
        sim.tick(step / sim.speed)
        t += step


def test_calm_boot_is_empty():
    _cfg, svc, sim = _mk()
    # nobody on the map, nobody dispatchable, nobody moving
    assert svc.positions == {}
    for row in svc.store.query("SELECT * FROM responders"):
        assert row["active"] == 0
    for r in sim.snapshot()["responders"]:
        assert r["on_duty"] is False
    # and the sim never files its own reports, no matter how long it runs
    _run(sim, 2 * 3600)
    assert svc.store.query("SELECT * FROM cases") == []
    assert svc.positions == {}


def test_duty_toggle_places_and_removes_rider():
    _cfg, svc, sim = _mk()
    assert sim.set_duty("resp_1", True, manual=True)
    assert "resp_1" in svc.positions
    assert "resp_1" in sim.manual
    row = svc.store.one("SELECT * FROM responders WHERE id='resp_1'")
    assert row["active"] == 1
    # the on-duty spot is ON the road network (home spot is snapped)
    lat, lng = svc.positions["resp_1"]
    snap = sim.graph._snap(lat, lng, __import__("pukaar.routing", fromlist=["SPEEDS_KMH"]).SPEEDS_KMH["walk"])
    assert snap is not None and snap.approach_m < 1.0
    # standing still while idle: no drift, ever
    _run(sim, 1800)
    assert svc.positions["resp_1"] == (lat, lng)
    # off duty while idle -> gone from the map and the candidate pool
    assert sim.set_duty("resp_1", False, manual=True)
    assert "resp_1" not in svc.positions
    assert svc.store.one("SELECT * FROM responders WHERE id='resp_1'")["active"] == 0


def test_offer_goes_only_to_on_duty_rider():
    _cfg, svc, sim = _mk()
    sim.set_duty("resp_1", True, manual=True)   # manual: a human will accept
    sim.run_scenario("injured_flyover")
    _run(sim, 60)
    assigned = {a["responder_id"] for a in svc.store.query("SELECT * FROM assignments")}
    assert assigned == {"resp_1"}


def test_full_calm_delivery_via_depot_on_roads():
    _cfg, svc, sim = _mk()
    sim.set_duty("resp_1", True, manual=True)
    sim.run_scenario("injured_flyover")
    _run(sim, 30)
    a = svc.store.one("SELECT * FROM assignments WHERE responder_id='resp_1'")
    assert a is not None
    assert svc.dispatch.respond(a["id"], True)   # the human taps ACCEPT

    r = sim._resp["resp_1"]
    _run(sim, 10)
    assert r["state"] == "enroute"
    # kit run first: the route goes via a depot, and it's a real polyline
    assert r["depot_id"] is not None and r["picked_up"] is False
    assert r["route"] is not None and len(r["route"]) > 2

    # drive it: pickup must happen before arrival
    _run(sim, 3600)
    assert r.get("picked_up") is True
    kit_events = [e for e in svc.feed if e["kind"] == "kit_pickup"]
    assert kit_events, "kit pickup never fired"
    assert r["state"] == "onsite"
    # a manual rider is a human: the sim must NOT record their outcome
    order = svc.store.one("SELECT * FROM orders")
    assert order["status"] == "onsite"
    # the human taps "served" in the app (same calls the endpoint makes)
    assert svc.dispatch.close(order["id"], "served")
    sim.settle_kit(order["id"], "served")
    svc.notify_outcome(order["case_id"], "served")
    assert svc.store.one("SELECT * FROM orders")["status"] == "closed"


def test_off_duty_mid_job_finishes_then_leaves():
    _cfg, svc, sim = _mk()
    sim.set_duty("resp_1", True, manual=True)
    sim.run_scenario("injured_flyover")
    _run(sim, 30)
    a = svc.store.one("SELECT * FROM assignments WHERE responder_id='resp_1'")
    svc.dispatch.respond(a["id"], True)
    _run(sim, 10)
    assert sim._resp["resp_1"]["state"] == "enroute"
    # asks to leave mid-delivery: stays on the map until the job closes
    sim.set_duty("resp_1", False, manual=True)
    assert "resp_1" in svc.positions
    sim.manual.discard("resp_1")     # sim finishes the job (dwell + close)
    _run(sim, 4 * 3600)
    assert svc.store.one("SELECT * FROM orders")["status"] in ("closed", "escalated")
    assert "resp_1" not in svc.positions


def test_ambient_manual_release_does_not_bench():
    _cfg, svc, sim = _mk(ambient=True)
    assert "resp_1" in svc.positions          # ambient boots everyone on duty
    sim.set_duty("resp_1", True, manual=True)
    sim.set_duty("resp_1", False, manual=True)
    # releasing the takeover hands back to the sim; the rider stays on shift
    assert sim._resp["resp_1"]["on_duty"] is True
    assert "resp_1" in svc.positions


def test_release_and_rewave_unsticks_an_accepted_order(svc, clock):
    """NGO-ops: the honest unstick — a job the rider can never finish goes
    back to the wave cycle with an audit row, never a false outcome."""
    svc.store.insert("responders", {
        "id": "resp_a", "partner_id": "partner_1", "display_name": "A",
        "medical": 1, "vetting": "verified", "active": 1})
    svc.positions["resp_a"] = (28.5933, 77.2507)
    svc.store.insert("responders", {
        "id": "resp_b", "partner_id": "partner_1", "display_name": "B",
        "medical": 1, "vetting": "verified", "active": 1})
    svc.positions["resp_b"] = (28.5940, 77.2510)
    svc.wa_inbound("+915555", "text", "aadmi ghayal hai patti chahiye")
    svc.wa_inbound("+915555", "location", lat=28.5933, lng=77.2507)
    svc.wa_inbound("+915555", "button", "fresh:10")
    clock.advance(5); svc.dispatch.tick()
    a = svc.store.one("SELECT * FROM assignments WHERE responder_id='resp_a' AND responded_at IS NULL")
    assert svc.dispatch.respond(a["id"], True)
    order = svc.store.one("SELECT * FROM orders")
    assert order["status"] == "accepted"
    assert svc.dispatch.release(order["id"], "phone died")
    order = svc.store.one("SELECT * FROM orders")
    assert order["status"] == "queued" and order["responder_id"] is None
    assert svc.store.query("SELECT * FROM audit_log WHERE action='released_rewave'")
    clock.advance(5); svc.dispatch.tick()   # fresh wave goes out
    asgs = svc.store.query("SELECT * FROM assignments WHERE responded_at IS NULL")
    assert asgs, "release did not re-wave"


def test_stop_deletes_conversation_and_keeps_hashed_audit(svc, clock):
    svc.wa_inbound("+916666", "text", "aadmi ghayal hai")
    out = svc.wa_inbound("+916666", "text", "STOP")
    assert [m.string_id for m in out] == ["S-STOP"]
    assert svc.store.one("SELECT * FROM conversations WHERE phone='+916666'") is None
    assert "+916666" not in svc.conversations
    rows = svc.store.query("SELECT * FROM audit_log WHERE action='witness_stop'")
    assert rows and "+916666" not in str(rows)   # hashed, never the number
    assert svc.wa_inbound("+916666", "text", "wahan phir koi hai")  # re-opens


def test_manual_assign_is_a_consent_offer_by_default(svc, clock):
    """NGO-ops: the accept tap is the covenant — a coordinator hand-off
    creates a priority offer the rider must still tap, not a fait
    accompli. force=True remains for phone-confirmed assigns."""
    svc.store.insert("responders", {
        "id": "resp_c", "partner_id": "partner_1", "display_name": "C",
        "medical": 1, "vetting": "verified", "active": 1})
    svc.positions["resp_c"] = (28.5933, 77.2507)
    svc.wa_inbound("+917777", "text", "aadmi ghayal hai patti chahiye")
    svc.wa_inbound("+917777", "location", lat=28.5933, lng=77.2507)
    svc.wa_inbound("+917777", "button", "fresh:10")
    order = svc.store.one("SELECT * FROM orders")
    assert svc.dispatch.manual_assign(order["id"], "resp_c")
    order = svc.store.one("SELECT * FROM orders")
    assert order["status"] == "offered" and order["responder_id"] is None
    a = svc.store.one("SELECT * FROM assignments WHERE responder_id='resp_c' "
                      "AND responded_at IS NULL")
    assert a is not None
    assert svc.dispatch.respond(a["id"], True)   # the rider consents
    assert svc.store.one("SELECT * FROM orders")["status"] == "accepted"


def test_shift_counts_only_real_112_redirects(svc, clock):
    """Reviewer P2: the handover's '112 redirects — check by hand' row was
    counting every case-less report row (abandoned half-intakes included).
    Only actual gate trips may count, via their durable audit rows."""
    svc.wa_inbound("+918881", "text", "ek aadmi hai station ke paas")  # half-intake
    assert svc.shift_summary(svc.now())["bounced_112"] == 0
    svc.wa_inbound("+918882", "text", "bahut khoon beh raha hai jaldi aao")
    assert svc.shift_summary(svc.now())["bounced_112"] == 1
    rows = svc.store.query(
        "SELECT * FROM audit_log WHERE action='emergency_redirect'")
    assert rows and "+918882" not in str(rows)   # hashed, never the number


def test_stock_adjust_endpoint(svc, clock):
    from fastapi.testclient import TestClient
    from pukaar.api import build_app
    from pukaar.config import Config
    cfg = Config(); cfg.backend = "mock"; cfg.sim_ambient = False
    client = TestClient(build_app(cfg))
    before = client.get("/api/state").json()["metrics"]["kits"]["MED-1"]
    r = client.post("/api/stock/adjust", json={
        "depot_id": "depot_basti", "sku": "MED-1", "delta": 5,
        "reason": "monthly donation received"})
    assert r.status_code == 200
    after = client.get("/api/state").json()["metrics"]["kits"]["MED-1"]
    assert after == before + 5
    assert client.post("/api/stock/adjust", json={
        "depot_id": "depot_basti", "sku": "MED-1", "delta": 2, "reason": " "}).status_code == 422
    assert client.post("/api/stock/adjust", json={
        "depot_id": "nope", "sku": "MED-1", "delta": 1, "reason": "x"}).status_code == 404
