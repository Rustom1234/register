"""Golden-run scenario (guaranteed clean P1 arc) and the restock rail."""

from pukaar.config import Config
from pukaar.db import Store
from pukaar.service import PukaarService
from pukaar.sim import Sim


def _mk():
    cfg = Config()
    cfg.backend = "mock"
    holder = {}
    svc = PukaarService(cfg, Store(":memory:"), now_fn=lambda: holder["sim"].sim_now)
    sim = Sim(svc, cfg, seed=42)
    holder["sim"] = sim
    sim._random_report_at = float("inf")
    return cfg, svc, sim


def _run(sim, sim_seconds, step=5.0):
    t = 0.0
    while t < sim_seconds:
        sim.tick(step / sim.speed)
        t += step


def test_golden_run_clean_arc():
    cfg, svc, sim = _mk()
    msg = sim.run_scenario("golden_run")
    assert "staged" in msg

    order = svc.store.one("SELECT * FROM orders")
    assert order is not None
    assert order["priority"] == "P1"
    assert order["clinical_flag"] == 1
    golden_resp = sim.golden[order["id"]]

    _run(sim, 2 * 3600)

    order = svc.store.one("SELECT * FROM orders")
    assert order["status"] == "closed"
    assert order["responder_id"] == golden_resp
    resp = svc.store.one("SELECT * FROM responders WHERE id=?", (golden_resp,))
    assert resp["medical"] == 1

    out = svc.store.one("SELECT * FROM outcomes")
    assert out["escalated"] == 1
    assert out["escalation_completed_at"] is not None

    kinds = [e["kind"] for e in svc.feed]
    for expected in ("case_created", "order_created", "wave_started",
                     "order_accepted", "responder_arrived", "outcome", "escalation_complete"):
        assert expected in kinds, f"missing {expected} in arc"


def test_golden_run_is_repeatable():
    for seed in (1, 2, 3):
        cfg, svc, sim = _mk()
        sim.rng.seed(seed)
        sim.run_scenario("golden_run")
        _run(sim, 2 * 3600)
        out = svc.store.one("SELECT * FROM outcomes")
        assert out is not None and out["escalated"] == 1


def test_restock_triggers_and_delivers():
    # Depot world: stock and the courier rail are per (depot, sku).
    cfg, svc, sim = _mk()
    svc.store.execute(
        "UPDATE inventory SET count=4 WHERE partner_id='depot_basti' AND sku='MED-1'")
    sim._consume_kit("MED-1", "depot_basti")
    row = svc.store.one(
        "SELECT count FROM inventory WHERE partner_id='depot_basti' AND sku='MED-1'")
    assert row["count"] == 3                      # at threshold -> flagged
    assert any(e["kind"] == "restock_needed" and e.get("depot") == "Basti Office"
               for e in svc.feed)
    assert ("depot_basti", "MED-1") in sim._pending_restocks

    _run(sim, 700)
    row = svc.store.one(
        "SELECT count FROM inventory WHERE partner_id='depot_basti' AND sku='MED-1'")
    assert row["count"] == 11                     # 3 + 8 courier top-up
    assert any(e["kind"] == "restock_delivered" for e in svc.feed)
    assert ("depot_basti", "MED-1") not in sim._pending_restocks


def test_restock_flag_not_duplicated():
    cfg, svc, sim = _mk()
    svc.store.execute(
        "UPDATE inventory SET count=4 WHERE partner_id='depot_east' AND sku='FOOD-1'")
    sim._consume_kit("FOOD-1", "depot_east")
    sim._consume_kit("FOOD-1", "depot_east")
    needed = [e for e in svc.feed if e["kind"] == "restock_needed" and e["sku"] == "FOOD-1"]
    assert len(needed) == 1


def test_done_conversation_absorbs_stray_buttons(svc):
    phone = "+91-G1"
    svc.wa_inbound(phone, "text", text="aadmi ghayal hai patti se khoon")
    svc.wa_inbound(phone, "location", lat=28.5933, lng=77.2507)
    svc.wa_inbound(phone, "photo", photo_hint="wound photo")
    assert svc.conversations[phone].state["stage"] == "done"
    replies = svc.wa_inbound(phone, "button", text="fresh:10")
    assert replies == []          # no re-ask after the report is filed


def test_done_conversation_allows_new_report(svc):
    phone = "+91-G2"
    svc.wa_inbound(phone, "text", text="aadmi ghayal hai patti se khoon")
    svc.wa_inbound(phone, "location", lat=28.5933, lng=77.2507)
    svc.wa_inbound(phone, "photo", photo_hint="wound photo")
    assert len(svc.store.query("SELECT * FROM cases")) == 1
    # a genuinely new report, far away, same witness
    svc.wa_inbound(phone, "text", text="ek aur aadmi bhooka hai station par")
    svc.wa_inbound(phone, "location", lat=28.62, lng=77.28)
    svc.wa_inbound(phone, "button", text="fresh:10")
    assert len(svc.store.query("SELECT * FROM cases")) == 2
