"""The standalone responder app (/responder): page served, and the API
surface it drives — duty toggle, offer accept, auto-arrival, outcome —
works end to end through the HTTP layer exactly as the page uses it."""

from fastapi.testclient import TestClient

from pukaar import geo
from pukaar.api import build_app
from pukaar.config import Config


def _client():
    cfg = Config()
    cfg.backend = "mock"
    return TestClient(build_app(cfg))


def _tick(sim, real_dt: float) -> None:
    # the sim is kept paused so the app's background loop can't interleave;
    # flip it on only for our own deterministic ticks
    sim.running = True
    sim.tick(real_dt)
    sim.running = False


def test_responder_page_served():
    with _client() as client:
        r = client.get("/responder")
        assert r.status_code == 200
        assert "responder app" in r.text
        assert "/static/responder.js" in r.text
        js = client.get("/static/responder.js")
        assert js.status_code == 200 and "/api/responder" in js.text


def test_state_carries_offer_ttl():
    with _client() as client:
        s = client.get("/api/state").json()
        assert s["config"]["offer_ttl_s"] > 0


def test_full_shift_through_http():
    """Duty on -> report near me -> offer -> accept -> sim drives me to the
    pin (auto-arrive) -> outcome stays mine to record -> served -> idle."""
    with _client() as client:
        app = client.app
        sim, svc = app.state.sim, app.state.svc
        sim.running = False
        base = (svc.cfg.zone_lat, svc.cfg.zone_lng)

        # go on duty as resp_1 (what the duty button posts)
        r = client.post("/api/manual", json={"responder_id": "resp_1", "manual": True})
        assert "resp_1" in r.json()["manual"]

        # park me 400 m from the pin, everyone else far — I'm wave 1 for sure
        for rid, resp in sim._resp.items():
            away = 400 if rid == "resp_1" else 1900
            resp["lat"], resp["lng"] = geo.offset_m(*base, away, 0)
            resp["state"], resp["target"] = "idle", None
            svc.positions[rid] = (resp["lat"], resp["lng"])

        for msg in (
            {"phone": "+91-SHIFT", "kind": "text", "text": "aadmi ghayal hai, pair se khoon"},
            {"phone": "+91-SHIFT", "kind": "location", "lat": base[0], "lng": base[1]},
            {"phone": "+91-SHIFT", "kind": "button", "text": "fresh:10"},
        ):
            client.post("/api/wa/inbound", json=msg)
        svc.dispatch.tick()

        # the app's offer query: my unanswered assignment on an offered order
        s = client.get("/api/state").json()
        offers = [a for a in s["assignments"]
                  if a["responder_id"] == "resp_1" and not a["responded_at"]]
        assert offers, "nearest manual responder should be in wave 1"

        r = client.post("/api/responder",
                        json={"action": "accept", "assignment_id": offers[0]["id"]})
        assert r.json()["ok"]

        def my_order():
            return svc.store.one("SELECT * FROM orders WHERE responder_id='resp_1'")

        for _ in range(60):                       # sim drives me to the pin
            _tick(sim, 5.0)
            if my_order()["status"] == "onsite":
                break
        assert my_order()["status"] == "onsite", "manual responder should auto-arrive"

        for _ in range(30):                       # dwell passes; still no auto-close
            _tick(sim, 5.0)
        assert my_order()["status"] == "onsite", "outcome must stay with the human"

        order = my_order()
        r = client.post("/api/responder",
                        json={"action": "outcome", "order_id": order["id"], "outcome": "served"})
        assert r.json()["ok"]
        s = client.get("/api/state").json()
        mine_active = [o for o in s["orders"]
                       if o["responder_id"] == "resp_1" and o["status"] in ("accepted", "onsite")]
        assert not mine_active                    # app returns to the idle screen
        out = svc.store.one("SELECT * FROM outcomes WHERE case_id=?", (order["case_id"],))
        assert out["served"] == 1

        # off duty (what the off-duty button posts)
        r = client.post("/api/manual", json={"responder_id": "resp_1", "manual": False})
        assert "resp_1" not in r.json()["manual"]
