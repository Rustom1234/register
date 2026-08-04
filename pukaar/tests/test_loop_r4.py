"""Loop round 4 — regression pins: zombie-case expiry, provenance
re-verifiability from stored rows, golden-run merge honesty."""

from pukaar import retention
from pukaar.config import Config
from pukaar.db import Store
from pukaar.provenance import Provenance
from pukaar.service import PukaarService
from pukaar.sim import Sim


def _mk(seed: int = 42):
    cfg = Config()
    cfg.backend = "mock"
    holder = {}
    svc = PukaarService(cfg, Store(":memory:"), now_fn=lambda: holder["sim"].sim_now)
    sim = Sim(svc, cfg, seed=seed)
    holder["sim"] = sim
    sim._random_report_at = float("inf")
    return svc, sim


def _report(svc, phone, lat=28.5933, lng=77.2507):
    svc.wa_inbound(phone, "text", text="flyover ke neeche aadmi ghayal hai, khoon")
    svc.wa_inbound(phone, "location", lat=lat, lng=lng)
    svc.wa_inbound(phone, "button", text="fresh:10")


def test_expired_open_case_is_closed_by_retention():
    svc, sim = _mk()
    _report(svc, "+91-Z1")
    case = svc.store.one("SELECT * FROM cases")
    assert case["status"] != "closed"

    # inside the 72h contract: purge must NOT touch it
    stats = retention.purge(svc.store, svc.cfg, sim.sim_now + 3600)
    assert stats["expired"] == 0

    # past expires_at: the zombie is closed, its orders released, audited
    stats = retention.purge(svc.store, svc.cfg, case["expires_at"] + 60)
    assert stats["expired"] == 1
    after = svc.store.one("SELECT * FROM cases WHERE id=?", (case["id"],))
    assert after["status"] == "closed" and after["closed_at"] is not None
    assert not svc.store.query(
        "SELECT * FROM orders WHERE case_id=? AND status NOT IN ('closed','escalated')",
        (case["id"],))
    assert svc.store.query(
        "SELECT * FROM audit_log WHERE action='case_expired' AND object_id=?", (case["id"],))

    # ...and the normal clocks now run: pin nulls once closed + ttl
    stats = retention.purge(svc.store, svc.cfg,
                            case["expires_at"] + svc.cfg.latlng_ttl_s + 120)
    gone = svc.store.one("SELECT * FROM cases WHERE id=?", (case["id"],))
    if gone is not None:   # row may already be past its 90d aggregation too
        assert gone["lat"] is None and gone["lng"] is None


def test_order_hmac_verifies_from_the_stored_row():
    svc, sim = _mk()
    _report(svc, "+91-H1")
    row = svc.store.one("SELECT * FROM orders")
    assert row and row["hmac"]
    # An auditor holds only the ROW: ints, not the bools the signer had.
    payload = {k: row[k] for k in ("sku", "priority", "clinical_flag")}
    assert isinstance(row["clinical_flag"], int)
    assert svc.prov.verify("agent_inferred", payload, row["hmac"]), \
        "the stored mac must be re-verifiable from the stored representation"


def test_bool_and_int_payloads_sign_identically():
    p = Provenance("k")
    assert p.sign("agent_inferred", {"clinical_flag": True}) == \
        p.sign("agent_inferred", {"clinical_flag": 1})
    assert p.sign("agent_inferred", {"clinical_flag": False}) == \
        p.sign("agent_inferred", {"clinical_flag": 0})
    # canonicalization must not collapse distinct non-bool values
    assert p.sign("agent_inferred", {"n": 2}) != p.sign("agent_inferred", {"n": 3})


def test_near_open_case_probe_matches_dedup():
    svc, sim = _mk()
    lat, lng = 28.5933, 77.2507
    _report(svc, "+91-G1", lat, lng)
    assert sim._near_open_case(lat, lng), "a fresh open case must be detected"
    assert not sim._near_open_case(lat + 0.02, lng + 0.02), \
        "a clear spot 2km away must not collide"
    svc.store.update("cases", svc.store.one("SELECT id FROM cases")["id"],
                     {"status": "closed"})
    assert not sim._near_open_case(lat, lng), "closed cases must not block staging"


def test_restocks_exposed_to_coordinator_state():
    svc, sim = _mk(seed=77)
    depot_id = sim.depot_list[0][0]
    for _ in range(20):
        sim._consume_kit("MED-1", depot_id)
    view = sim.restocks_view()
    assert view and view[0]["sku"] == "MED-1"
    assert view[0]["depot"] == sim.depot_list[0][1]   # display name, not id
    assert view[0]["due_s"] >= 0


def test_inbound_client_id_dedupes_redelivery():
    from fastapi.testclient import TestClient

    from pukaar.api import build_app
    cfg = Config()
    cfg.backend = "mock"
    client = TestClient(build_app(cfg))
    client.__enter__()
    body = {"phone": "+91-IDP1", "kind": "text",
            "text": "aadmi ghayal hai, patti se khoon", "client_id": "abc123"}
    r1 = client.post("/api/wa/inbound", json=body)
    assert r1.status_code == 200 and r1.json()["replies"]
    r2 = client.post("/api/wa/inbound", json=body)   # outbox redelivery
    assert r2.status_code == 200 and r2.json()["replies"] == []
    # same witness, NEW message id -> processed normally
    r3 = client.post("/api/wa/inbound", json={**body, "client_id": "def456",
                                              "text": "abhi bhi wahin hai"})
    assert r3.json()["replies"]
