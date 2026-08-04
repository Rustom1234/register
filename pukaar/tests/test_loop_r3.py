"""Loop round 3 — regression pins for the audit-fleet-confirmed fixes.

The heavyweight one is the restart-mid-delivery ledger: reservations move
DURABLE inventory at accept, so the ledger itself must survive a process
restart or stock drifts permanently (double-consume at re-attach, orphaned
returns). The rest pin the CAS close, the recheck-cancel settlement, the
inbound flood cap, the trimmed health probe, and the push lifecycle.
"""

import json

from fastapi.testclient import TestClient

from pukaar.api import build_app
from pukaar.config import Config
from pukaar.db import Store
from pukaar.service import PukaarService
from pukaar.sim import Sim


def _mk(seed: int = 42, store: Store | None = None):
    cfg = Config()
    cfg.backend = "mock"
    holder = {}
    svc = PukaarService(cfg, store or Store(":memory:"),
                        now_fn=lambda: holder["sim"].sim_now)
    sim = Sim(svc, cfg, seed=seed)
    holder["sim"] = sim
    sim._random_report_at = float("inf")
    return svc, sim


def _run(sim, sim_seconds, step=5.0):
    t = 0.0
    while t < sim_seconds:
        sim.tick(step / sim.speed)
        t += step


def _total_stock(sim) -> int:
    return sum(sum(d["stock"].values()) for d in sim.depots())


def _accepted_order(svc, sim, before, budget_s=2400):
    """Drive the sim until a scenario order is accepted (stock reserved)."""
    sim.run_scenario("hungry_elder")
    t = 0
    while _total_stock(sim) == before and t < budget_s:
        _run(sim, 20)
        t += 20
    assert _total_stock(sim) == before - 1, "acceptance must reserve a kit"
    order = svc.store.one("SELECT * FROM orders WHERE status IN ('accepted','onsite') "
                          "AND responder_id IS NOT NULL")
    assert order, "expected a live accepted order"
    return order


# ------------------------------------------------------------ P1: ledger --
def test_restart_mid_delivery_does_not_double_consume():
    store = Store(":memory:")
    svc1, sim1 = _mk(seed=7, store=store)
    before = _total_stock(sim1)
    order = _accepted_order(svc1, sim1, before)

    # --- restart: same DB, fresh process (fresh Sim over the same Store) ---
    svc2, sim2 = _mk(seed=8, store=store)
    assert _total_stock(sim2) == before - 1, \
        "boot re-seed must not reset stock moved by real activity"
    _run(sim2, 30)   # _sync_states re-attaches the enroute order
    assert _total_stock(sim2) == before - 1, \
        "re-attach after restart must NOT consume a second kit"
    # the restored ledger still owns the reservation: not_found returns it
    sim2.settle_kit(order["id"], "not_found")
    assert _total_stock(sim2) == before, \
        "settle after restart must return the restored reservation"


def test_pending_restock_survives_restart():
    store = Store(":memory:")
    svc1, sim1 = _mk(seed=11, store=store)
    # drain one depot/sku to threshold so a courier restock is owed
    depot_id = sim1.depot_list[0][0]
    for _ in range(20):
        sim1._consume_kit("MED-1", depot_id)
    assert sim1._pending_restocks, "drain should have armed a restock"
    # restart before the courier lands
    svc2, sim2 = _mk(seed=12, store=store)
    assert sim2._pending_restocks, \
        "an owed courier restock must survive a restart (depot stays dry forever otherwise)"


# ------------------------------------------------ P2: recheck-cancel leak --
def test_recheck_no_returns_reserved_kit():
    svc, sim = _mk(seed=21)
    before = _total_stock(sim)
    order = _accepted_order(svc, sim, before)
    phone = sim.last_scenario_phone
    conv = svc.conversations.get(phone)
    assert conv is not None
    conv.state["case_id"] = order["case_id"]

    svc._handle_recheck_reply(conv, "no")   # witness: person has moved on

    o = svc.store.one("SELECT * FROM orders WHERE id=?", (order["id"],))
    assert o["status"] == "closed"
    assert _total_stock(sim) == before, \
        "witness-cancel of an accepted order must put the reserved kit back"
    assert order["id"] not in sim._reservations
    assert any(e["kind"] == "kit_return" for e in svc.feed)


# --------------------------------------------------------- P2: CAS close --
def test_close_and_cancel_are_compare_and_swap():
    svc, sim = _mk(seed=31)
    before = _total_stock(sim)
    order = _accepted_order(svc, sim, before)

    first = svc.dispatch.close(order["id"], "served")
    assert first is not None
    second = svc.dispatch.close(order["id"], "served")
    assert second is None, "the losing closer must get None, not double-write"
    assert svc.dispatch.cancel(order["id"], "late witness cancel") is False

    outs = svc.store.query("SELECT * FROM outcomes WHERE case_id=?", (order["case_id"],))
    assert len(outs) == 1, "exactly one outcome row per closed order"


# ------------------------------------------- P3: escalated settle + timer --
def test_escalated_close_keeps_kit_consumed_then_completes():
    svc, sim = _mk(seed=41)
    before = _total_stock(sim)
    order = _accepted_order(svc, sim, before)

    assert svc.dispatch.close(order["id"], "escalated") is not None
    sim.settle_kit(order["id"], "escalated")
    assert _total_stock(sim) == before - 1, \
        "an escalated case KEEPS the kit (it was delivered) — only not_found/declined return it"
    # the api handler arms this for human closes; completing must not touch stock
    sim._pending_escalations[order["id"]] = sim.sim_now + 60
    _run(sim, 240)
    assert _total_stock(sim) == before - 1
    assert not svc.store.query(
        "SELECT * FROM orders WHERE id=? AND status='escalated'", (order["id"],)), \
        "escalation should complete and close the order"


# ------------------------------------------------- P2: dedupe window edge --
def test_dedupe_merges_inside_window_not_after_expiry_or_close():
    svc, sim = _mk(seed=51)
    lat, lng = 28.5933, 77.2507

    def report(phone):
        svc.wa_inbound(phone, "text", text="flyover ke neeche aadmi ghayal hai, khoon")
        svc.wa_inbound(phone, "location", lat=lat, lng=lng)
        svc.wa_inbound(phone, "button", text="fresh:10")

    report("+91-D1")
    report("+91-D2")
    cases = svc.store.query("SELECT * FROM cases")
    assert len(cases) == 1 and cases[0]["merged_witnesses"] == 2, \
        "same pin inside the window must merge, not open a twin case"

    sim.sim_now += svc.cfg.dedup_window_s + 60   # window expires
    report("+91-D3")
    cases = svc.store.query("SELECT * FROM cases ORDER BY created_at")
    assert len(cases) == 2, "an expired window must open a fresh case"

    svc.store.update("cases", cases[-1]["id"], {"status": "closed"})
    report("+91-D4")
    assert len(svc.store.query("SELECT * FROM cases")) == 3, \
        "a closed case must never swallow a new report"


# ------------------------------------- P2/P3: inbound door + health probe --
def test_inbound_validation_and_global_flood_cap():
    cfg = Config()
    cfg.backend = "mock"
    client = TestClient(build_app(cfg))
    client.__enter__()

    bad = client.post("/api/wa/inbound",
                      json={"phone": "<script>alert(1)</script>", "kind": "text", "text": "hi"})
    assert bad.status_code == 422

    nan = client.post("/api/wa/inbound",
                      content=b'{"phone": "+91-V1", "kind": "location", "lat": NaN, "lng": 77.25}',
                      headers={"content-type": "application/json"})
    assert nan.status_code == 422

    oob = client.post("/api/wa/inbound",
                      json={"phone": "+91-V1", "kind": "location", "lat": 91.0, "lng": 77.25})
    assert oob.status_code == 422

    # global cap: a flood minting a fresh phone per request must hit 429
    seen_429 = False
    for i in range(40):
        r = client.post("/api/wa/inbound",
                        json={"phone": f"+91-F{i}", "kind": "text", "text": "hello"})
        if r.status_code == 429:
            seen_429 = True
            break
    assert seen_429, "per-phone limits alone cannot stop a fresh-phone flood"

    # ...but an emergency text still gets through mid-flood
    er = client.post("/api/wa/inbound",
                     json={"phone": "+91-F999", "kind": "text", "text": "aadmi behosh pada hai!!"})
    assert er.status_code == 200


def test_health_trims_operational_data_without_staff_auth():
    import os
    os.environ["PUKAAR_ADMIN_TOKEN"] = "sesame"
    try:
        cfg = Config()
        cfg.backend = "mock"
        client = TestClient(build_app(cfg))
        client.__enter__()
        anon = client.get("/health").json()
        assert anon["ok"] is True and "tick_age_s" in anon
        assert "backend" not in anon and "cases" not in anon and "sim_now" not in anon
        staffed = client.get("/health", headers={"x-wayside-token": "sesame"}).json()
        assert "backend" in staffed and "cases" in staffed
    finally:
        del os.environ["PUKAAR_ADMIN_TOKEN"]


# ------------------------------------------------------ P2: push lifecycle --
def test_push_key_survives_restart_and_dead_subs_prune(monkeypatch):
    import pytest

    import pukaar.push as push_mod
    if not push_mod._PUSH_OK:
        pytest.skip("push stack not installed")

    store = Store(":memory:")
    p1 = push_mod.PushService(store)
    key = p1.vapid_public_key()
    assert key
    p2 = push_mod.PushService(store)
    assert p2.vapid_public_key() == key, \
        "a restart must reuse the stored VAPID key — rotation kills every old subscription"

    sub = {"endpoint": "https://push.example/a", "keys": {"auth": "x", "p256dh": "y"}}
    p2.subscribe("resp_1", sub)
    p2.subscribe("resp_1", {**sub, "keys": {"auth": "x2", "p256dh": "y2"}})
    assert len(store.query("SELECT * FROM push_subs")) == 1, "endpoint replaces, not duplicates"

    class _Gone:
        status_code = 410

    def _dead(*a, **k):
        raise push_mod.WebPushException("gone", response=_Gone())

    monkeypatch.setattr(push_mod, "webpush", _dead)
    p2._send_all(store.query("SELECT endpoint, sub FROM push_subs"), "{}")
    assert store.query("SELECT * FROM push_subs") == [], "410 must prune the subscription"

    # protocol rejections (401/403) prune only after repeated strikes
    p2.subscribe("resp_1", sub)

    class _Forbidden:
        status_code = 403

    def _reject(*a, **k):
        raise push_mod.WebPushException("forbidden", response=_Forbidden())

    monkeypatch.setattr(push_mod, "webpush", _reject)
    rows = store.query("SELECT endpoint, sub FROM push_subs")
    for _ in range(4):
        p2._send_all(rows, "{}")
        assert len(store.query("SELECT * FROM push_subs")) == 1
    p2._send_all(rows, "{}")   # fifth strike
    assert store.query("SELECT * FROM push_subs") == []
