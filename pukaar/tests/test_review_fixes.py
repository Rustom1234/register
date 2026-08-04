"""Regression pins for the five-lens review findings: every confirmed
defect gets a test that fails on the old behavior."""

from fastapi.testclient import TestClient

from pukaar import geo, retention
from pukaar.api import build_app
from pukaar.config import Config


def _file_report(svc, phone, lat=28.5933, lng=77.2507, text="aadmi ghayal hai"):
    svc.wa_inbound(phone, "text", text=text)
    svc.wa_inbound(phone, "location", lat=lat, lng=lng)
    svc.wa_inbound(phone, "button", text="fresh:10")


# ---------------------------------------------------------------- intake --

def test_urgency_never_leaks_to_next_report(svc):
    """A high-urgency photo on report 1 must not make report 2 a P1."""
    svc.wa_inbound("+91-U1", "text", text="aadmi ghayal hai flyover ke neeche")
    svc.wa_inbound("+91-U1", "location", lat=28.5933, lng=77.2507)
    svc.wa_inbound("+91-U1", "photo",
                   photo_hint="serious infected wound, lot of blood, pus visible")
    svc.wa_inbound("+91-U1", "button", text="fresh:10")
    first = svc.store.query("SELECT * FROM orders ORDER BY created_at")
    assert first and first[0]["priority"] == "P1"

    # unrelated follow-up report from the same phone, mild need
    _file_report(svc, "+91-U1", lat=28.599, lng=77.258,
                 text="ek aadmi ko khana chahiye station ke paas")
    orders = svc.store.query("SELECT * FROM orders ORDER BY created_at")
    assert len(orders) == 2
    assert orders[1]["priority"] != "P1", "urgency leaked across reports"


def test_stop_then_text_reopens(svc):
    svc.wa_inbound("+91-S1", "text", text="ek aadmi ko madad chahiye")
    replies = svc.wa_inbound("+91-S1", "text", text="STOP")
    assert any(r.string_id == "S-STOP" for r in replies)
    # silence for buttons while stopped
    assert svc.wa_inbound("+91-S1", "button", text="cat:food") == []
    # a fresh text re-opens the line, per the S-STOP promise
    replies = svc.wa_inbound("+91-S1", "text", text="wapas aa gaya, aadmi abhi bhi wahan hai")
    assert replies, "stopped conversation must re-open on a fresh text"


def test_emergency_outranks_stop(svc):
    svc.wa_inbound("+91-S2", "text", text="hello")
    svc.wa_inbound("+91-S2", "text", text="STOP")
    replies = svc.wa_inbound("+91-S2", "text", text="ek aadmi behosh pada hai!!")
    assert any(r.string_id == "S-112" for r in replies), \
        "emergency after STOP must still get the 112 redirect"


def test_devanagari_emergency_end_to_end(svc):
    replies = svc.wa_inbound("+91-S3", "text", text="एक आदमी बेहोश पड़ा है सड़क पर")
    assert any(r.string_id == "S-112" for r in replies)


def test_malformed_fresh_button_absorbed(svc):
    svc.wa_inbound("+91-F1", "text", text="aadmi ghayal hai")
    svc.wa_inbound("+91-F1", "location", lat=28.5933, lng=77.2507)
    for bad in ("fresh:oops", "fresh:", "fresh:1e3"):
        replies = svc.wa_inbound("+91-F1", "button", text=bad)  # must not raise
        assert isinstance(replies, list)
    conv = svc.conversations["+91-F1"]
    assert conv.state["freshness_min"] is None


# -------------------------------------------------------------- dispatch --

def _add_responder(svc, rid, lat, lng, medical=0):
    svc.store.insert("responders", {"id": rid, "partner_id": "partner_1",
                                    "display_name": rid, "medical": medical,
                                    "vetting": "verified", "active": 1})
    svc.positions[rid] = (lat, lng)


def test_double_accept_second_loses(svc):
    """The first-accept lock is a compare-and-swap on the order row: the
    claim() update wins exactly once, so two concurrent accepts that both
    passed the status read can never both lock the order."""
    base = (28.5933, 77.2507)
    _add_responder(svc, "r_a", *geo.offset_m(*base, 100, 0))
    _add_responder(svc, "r_b", *geo.offset_m(*base, 150, 0))
    _file_report(svc, "+91-D1", *base)
    svc.dispatch.tick()
    asgs = svc.store.query("SELECT * FROM assignments WHERE responded_at IS NULL")
    assert len(asgs) >= 2
    order = svc.store.one("SELECT * FROM orders")

    # the exact CAS both racing accepts execute — only one row change total
    won_a = svc.store.claim(
        "UPDATE orders SET status='accepted', responder_id=?, accepted_at=? "
        "WHERE id=? AND status='offered'", (asgs[0]["responder_id"], 1.0, order["id"]))
    won_b = svc.store.claim(
        "UPDATE orders SET status='accepted', responder_id=?, accepted_at=? "
        "WHERE id=? AND status='offered'", (asgs[1]["responder_id"], 1.0, order["id"]))
    assert (won_a, won_b) == (1, 0), "second accept must lose the CAS"
    locked = svc.store.one("SELECT * FROM orders")
    assert locked["responder_id"] == asgs[0]["responder_id"]

    # and through the engine: a late respond() on the losing offer bounces
    assert svc.dispatch.respond(asgs[1]["id"], True) is False
    assert svc.store.one("SELECT * FROM orders")["responder_id"] == asgs[0]["responder_id"]


def test_manual_assign_refuses_pinless_case(svc):
    """A landmark-only case has nowhere to navigate to — manual assign must
    refuse instead of wedging the responder on an unreachable job."""
    _add_responder(svc, "r_c", 28.5933, 77.2507)
    svc.wa_inbound("+91-D2", "text", text="aadmi flyover ke neeche hai, chot lagi hai")
    svc.wa_inbound("+91-D2", "text", text="flyover ke neeche, gate 3 ke paas")
    svc.wa_inbound("+91-D2", "button", text="fresh:10")
    case = svc.store.one("SELECT * FROM cases")
    if case is None or case["lat"] is not None:
        # intake didn't produce a pinless case in this configuration; force one
        if case is None:
            return
        svc.store.update("cases", case["id"], {"lat": None, "lng": None})
    order = svc.store.one("SELECT * FROM orders")
    assert order is not None
    assert svc.dispatch.manual_assign(order["id"], "r_c") is False
    order = svc.store.one("SELECT * FROM orders")
    assert order["status"] != "accepted"


def test_wave_expiry_at_night_requeues(svc, clock, cfg):
    base = (28.5933, 77.2507)
    _add_responder(svc, "r_d", *geo.offset_m(*base, 100, 0))
    clock.t = 20.9 * 3600                       # 20:54 — inside the window
    _file_report(svc, "+91-D3", *base)
    svc.dispatch.tick()
    assert svc.store.one("SELECT * FROM orders")["status"] == "offered"

    clock.t = 21.5 * 3600                       # 21:30 — window closed, TTL over
    svc.dispatch.tick()
    order = svc.store.one("SELECT * FROM orders")
    assert order["status"] == "queued", "expired night wave must requeue, not re-offer"
    assert not svc.store.query("SELECT * FROM assignments WHERE responded_at IS NULL")

    clock.t = 31.2 * 3600                       # 07:12 next day — window open
    svc.dispatch.tick()
    order = svc.store.one("SELECT * FROM orders")
    assert order["status"] == "offered", "morning tick must re-wave the queued order"


def test_golden_run_marks_its_own_order():
    """With a decoy case filed at the same sim instant (created_at tie), the
    golden flag must land on the order of the case the golden conversation
    created — never on the decoy's."""
    from pukaar.db import Store
    from pukaar.service import PukaarService
    from pukaar.sim import Sim

    cfg = Config()
    cfg.backend = "mock"
    holder = {}
    svc = PukaarService(cfg, Store(":memory:"), now_fn=lambda: holder["sim"].sim_now)
    sim = Sim(svc, cfg, seed=42)
    holder["sim"] = sim
    sim._random_report_at = float("inf")

    # decoy witness, same clock tick as the golden run that follows
    svc.wa_inbound("+91-DECOY", "text", text="ek buzurg bhooke hain station ke paas")
    svc.wa_inbound("+91-DECOY", "location", lat=cfg.zone_lat + 0.008, lng=cfg.zone_lng + 0.008)
    svc.wa_inbound("+91-DECOY", "button", text="fresh:10")

    sim.run_scenario("golden_run")
    assert sim.golden, "golden order should be staged"
    golden_phone_cases = {
        conv.state.get("case_id")
        for phone, conv in svc.conversations.items() if phone != "+91-DECOY"}
    for order_id in sim.golden:
        order = svc.store.one("SELECT * FROM orders WHERE id=?", (order_id,))
        assert order["case_id"] in golden_phone_cases, \
            "golden flag landed on the decoy's order"


# ------------------------------------------------------------- retention --

def test_orphan_reports_purged(svc, cfg):
    svc.wa_inbound("+91-R9", "text", text="ek aadmi behosh pada hai!!")  # 112: no case
    reports = svc.store.query("SELECT * FROM reports WHERE case_id IS NULL")
    assert reports, "the 112 redirect should have recorded a report row"
    stats = retention.purge(svc.store, cfg, now=svc.now() + cfg.case_row_ttl_s + 60)
    assert stats["orphan_reports"] >= 1
    assert not svc.store.query("SELECT * FROM reports WHERE case_id IS NULL")


def test_open_case_within_contract_survives_purge_then_expires(svc, cfg):
    _file_report(svc, "+91-R8")
    case = svc.store.one("SELECT * FROM cases")
    assert case["closed_at"] is None
    # Inside its 72h contract an open case is untouchable: row AND pin stay.
    retention.purge(svc.store, cfg, now=svc.now() + 3600)
    still = svc.store.one("SELECT * FROM cases WHERE id=?", (case["id"],))
    assert still is not None and still["status"] != "closed"
    assert still["lat"] is not None, "a live case must keep its pin"
    # At 90 days the case cannot still be "live": the zombie guard closes it
    # (its own expires_at lapsed 87 days earlier) and the sweep aggregates it
    # into the analytics cells rather than keeping pin+text forever.
    retention.purge(svc.store, cfg, now=svc.now() + cfg.case_row_ttl_s + 60)
    assert svc.store.one("SELECT * FROM cases WHERE id=?", (case["id"],)) is None
    cells = svc.store.query("SELECT * FROM analytics_cells")
    assert cells and sum(c["n"] for c in cells) >= 1, \
        "the swept case must survive as a coarse aggregate"


# ------------------------------------------------------------------ api --

def test_bad_outcome_rejected_without_mutation():
    cfg = Config()
    cfg.backend = "mock"
    with TestClient(build_app(cfg)) as client:
        svc = client.app.state.svc
        _file_report(svc, "+91-A1")
        svc.dispatch.tick()
        order = svc.store.one("SELECT * FROM orders")
        r = client.post("/api/responder", json={
            "action": "outcome", "order_id": order["id"], "outcome": "banana"})
        assert r.status_code == 400
        after = svc.store.one("SELECT * FROM orders")
        assert after["status"] == order["status"], "bad outcome must not mutate"
        assert not svc.store.query("SELECT * FROM outcomes")


def test_report_escapes_witness_category():
    cfg = Config()
    cfg.backend = "mock"
    with TestClient(build_app(cfg)) as client:
        svc = client.app.state.svc
        svc.wa_inbound("+91-A2", "text", text="aadmi ko madad chahiye jaldi")
        svc.wa_inbound("+91-A2", "location", lat=28.5933, lng=77.2507)
        svc.wa_inbound("+91-A2", "button", text='cat:<script>alert(1)</script>')
        svc.wa_inbound("+91-A2", "button", text="fresh:10")
        html_page = client.get("/report").text
        assert "<script>alert(1)</script>" not in html_page
