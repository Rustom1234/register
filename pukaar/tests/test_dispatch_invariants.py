"""Property-style dispatch invariants under randomized drive.

Across random seeds we hammer the engine with interleaved order creation,
clock jumps, ticks, and random accept/decline/close actions, and after
every step assert the invariants that must NEVER break:

  I1  an order never has more than one accepted assignment
  I2  order.responder_id always matches its single accepted assignment
  I3  a released/late offer can never steal an accepted order
  I4  wave count never exceeds cfg.max_waves
  I5  a wave offers at most k responders, and they are the nearest
      eligible ones at offer time
  I6  live (unanswered) offers per order never exceed the wave size
"""

import random

from pukaar import geo
from pukaar.config import Config
from pukaar.db import Store, new_id
from pukaar.service import PukaarService

ZONE = (28.5933, 77.2507)


class Clock:
    def __init__(self):
        self.t = 10 * 3600.0

    def __call__(self):
        return self.t


def _mk(seed):
    cfg = Config()
    cfg.backend = "mock"
    clock = Clock()
    svc = PukaarService(cfg, Store(":memory:"), now_fn=clock)
    rng = random.Random(seed)
    for i in range(rng.randint(3, 8)):
        rid = f"r{i}"
        svc.store.insert("responders", {"id": rid, "partner_id": "partner_1",
                                        "display_name": rid, "medical": 0,
                                        "vetting": "verified", "active": 1})
        svc.positions[rid] = geo.offset_m(*ZONE, rng.uniform(-1200, 1200), rng.uniform(-1200, 1200))
    return cfg, clock, svc, rng


def _new_order(svc, rng):
    lat, lng = geo.offset_m(*ZONE, rng.uniform(-1000, 1000), rng.uniform(-1000, 1000))
    case = {"id": new_id("case"), "status": "routed", "category": "food", "category_conf": 1.0,
            "urgency": "medium", "cell": geo.cell_key(lat, lng), "lat": lat, "lng": lng,
            "geo_conf": "pin", "landmark_text": None, "freshness_min": 5, "detail": "",
            "merged_witnesses": 1, "created_at": svc.now(), "closed_at": None, "expires_at": None}
    svc.store.insert("cases", case)
    order = {"sku": "FOOD-1", "addons": [], "clinical_flag": rng.random() < 0.3,
             "priority": rng.choice(["P1", "P2"]), "instruction_ids": [],
             "confidence": 0.9, "needs_review": False, "created_by": "code", "kit": {}}
    return svc.dispatch.create_order(case, order, "mac")


def _eligible(svc, cfg, order):
    """Recompute eligibility the way a correct engine must see it."""
    already = {a["responder_id"] for a in svc.store.query(
        "SELECT responder_id FROM assignments WHERE order_id=?", (order["id"],))}
    open_counts = {r["responder_id"]: r["n"] for r in svc.store.query(
        "SELECT responder_id, COUNT(*) n FROM orders WHERE status IN ('accepted','onsite') "
        "GROUP BY responder_id")}
    case = svc.store.one("SELECT * FROM cases WHERE id=?", (order["case_id"],))
    out = []
    for rid, (lat, lng) in svc.positions.items():
        if rid in already or open_counts.get(rid, 0) >= cfg.responder_open_cap:
            continue
        out.append((geo.haversine_m(case["lat"], case["lng"], lat, lng), rid))
    return sorted(out)


def _check_invariants(svc, cfg, snapshot_before=None):
    for o in svc.store.query("SELECT * FROM orders"):
        acc = svc.store.query(
            "SELECT * FROM assignments WHERE order_id=? AND response='accepted'", (o["id"],))
        assert len(acc) <= 1, f"I1 broken: {o['id']} has {len(acc)} accepts"
        if o["responder_id"] is not None:
            assert acc and acc[0]["responder_id"] == o["responder_id"], "I2 broken"
        assert o["wave"] <= cfg.max_waves, "I4 broken"
        live = svc.store.query(
            "SELECT * FROM assignments WHERE order_id=? AND responded_at IS NULL", (o["id"],))
        k = cfg.wave_size_p1 if o["priority"] == "P1" else cfg.wave_size_default
        assert len(live) <= k, "I6 broken"


def _drive(seed):
    cfg, clock, svc, rng = _mk(seed)
    orders = []
    for _ in range(160):
        action = rng.random()
        if action < 0.18:
            orders.append(_new_order(svc, rng))
        elif action < 0.5:
            # I5: verify wave candidates are the nearest eligible at offer time
            queued = svc.store.query("SELECT * FROM orders WHERE status='queued'")
            expectations = {}
            for o in queued:
                k = cfg.wave_size_p1 if o["priority"] == "P1" else cfg.wave_size_default
                expectations[o["id"]] = [rid for _, rid in _eligible(svc, cfg, o)[:k]]
            svc.dispatch.tick()
            for oid, expected in expectations.items():
                offered = {a["responder_id"] for a in svc.store.query(
                    "SELECT * FROM assignments WHERE order_id=? AND responded_at IS NULL", (oid,))}
                if expected:
                    assert offered == set(expected), f"I5 broken: {offered} != {expected}"
        elif action < 0.62:
            clock.t += rng.choice([10, 45, cfg.offer_ttl_s + 5])
        elif action < 0.88:
            pending = svc.store.query(
                "SELECT * FROM assignments WHERE responded_at IS NULL ORDER BY offered_at")
            if pending:
                a = rng.choice(pending)
                svc.dispatch.respond(a["id"], rng.random() < 0.5)
        else:
            active = svc.store.query(
                "SELECT * FROM orders WHERE status IN ('accepted','onsite')")
            if active:
                o = rng.choice(active)
                svc.dispatch.arrived(o["id"])
                svc.dispatch.close(o["id"], rng.choice(["served", "not_found", "declined"]))
        _check_invariants(svc, cfg)

    # I3 explicitly: released offers can never steal
    for o in svc.store.query("SELECT * FROM orders WHERE status IN ('accepted','onsite')"):
        released = svc.store.query(
            "SELECT * FROM assignments WHERE order_id=? AND response IN ('released','declined','timeout')",
            (o["id"],))
        owner = o["responder_id"]
        for a in released:
            svc.dispatch.respond(a["id"], True)   # a very late, very eager accept
        o2 = svc.store.one("SELECT * FROM orders WHERE id=?", (o["id"],))
        assert o2["responder_id"] == owner, "I3 broken: released offer stole the order"
    _check_invariants(svc, cfg)


def test_dispatch_invariants_across_seeds():
    for seed in range(10):
        _drive(seed)
