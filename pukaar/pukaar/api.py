"""FastAPI app — serves the demo control room and the (simulated) WhatsApp line.

Single process: a 1s background loop advances the sim clock, the dispatch
engine, and a periodic retention purge. The UI polls /api/state.
"""

import asyncio
import pathlib
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import Config
from .db import Store
from .service import PukaarService
from .sim import SCENARIOS, Sim

STATIC = pathlib.Path(__file__).parent / "static"


class Inbound(BaseModel):
    phone: str
    kind: str  # text | button | location | photo
    text: str | None = None
    lat: float | None = None
    lng: float | None = None
    photo_hint: str | None = None


class SimCtl(BaseModel):
    action: str            # pause | resume | speed
    value: float | None = None


class RespAction(BaseModel):
    action: str            # accept | decline | outcome
    assignment_id: str | None = None
    order_id: str | None = None
    outcome: str | None = None


def build_app(cfg: Config | None = None) -> FastAPI:
    cfg = cfg or Config()
    store = Store(":memory:")  # demo runs in-memory; point at a file for persistence
    holder: dict = {}
    svc = PukaarService(cfg, store, now_fn=lambda: holder["sim"].sim_now if "sim" in holder else 0.0)
    sim = Sim(svc, cfg)
    holder["sim"] = sim

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = asyncio.create_task(_loop())
        yield
        task.cancel()

    async def _loop() -> None:
        last = time.monotonic()
        last_purge = 0.0
        while True:
            await asyncio.sleep(1.0)
            now = time.monotonic()
            sim.tick(now - last)
            last = now
            if sim.sim_now - last_purge > 6 * 3600:  # purge every 6 sim-hours
                svc.run_purge()
                last_purge = sim.sim_now

    app = FastAPI(title="Pukaar demo", lifespan=lifespan)
    app.state.svc, app.state.sim = svc, sim

    # ------------------------------------------------------------ inbound --
    @app.post("/api/wa/inbound")
    def wa_inbound(msg: Inbound):
        replies = svc.wa_inbound(msg.phone, msg.kind, text=msg.text, lat=msg.lat,
                                 lng=msg.lng, photo_hint=msg.photo_hint)
        return {"replies": [{"text": r.text, "buttons": r.buttons, "id": r.string_id} for r in replies]}

    # ------------------------------------------------------------- state --
    @app.get("/api/state")
    def state():
        cases = svc.store.query(
            "SELECT * FROM cases ORDER BY created_at DESC LIMIT 60")
        orders = svc.store.query(
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT 60")
        for c in cases:
            c["digipin"] = svc.digipin_for(c["lat"], c["lng"])
        return {
            "backend": svc.backend.name,
            "prov_ephemeral": svc.prov.ephemeral,
            "zone": {"lat": cfg.zone_lat, "lng": cfg.zone_lng, "radius_m": cfg.zone_radius_m},
            "sim": sim.snapshot(),
            "cases": cases,
            "orders": orders,
            "assignments": svc.store.query(
                "SELECT * FROM assignments ORDER BY offered_at DESC LIMIT 40"),
            "feed": list(svc.feed)[-45:][::-1],
            "metrics": svc.metrics(),
            "conversations": {
                phone: conv.log[-30:] for phone, conv in list(svc.conversations.items())[-6:]
            },
        }

    # ---------------------------------------------------------- scenarios --
    @app.post("/api/scenario/{name}")
    def scenario(name: str):
        if name not in SCENARIOS:
            raise HTTPException(404, f"unknown scenario: {name}")
        return {"result": sim.run_scenario(name)}

    @app.post("/api/sim")
    def sim_ctl(ctl: SimCtl):
        if ctl.action == "pause":
            sim.running = False
        elif ctl.action == "resume":
            sim.running = True
        elif ctl.action == "speed" and ctl.value:
            sim.speed = max(0.5, min(60.0, ctl.value))
        return {"running": sim.running, "speed": sim.speed}

    @app.post("/api/purge")
    def run_purge():
        return svc.run_purge()

    @app.post("/api/responder")
    def responder_action(act: RespAction):
        if act.action in ("accept", "decline") and act.assignment_id:
            ok = svc.dispatch.respond(act.assignment_id, act.action == "accept")
            return {"ok": ok}
        if act.action == "outcome" and act.order_id and act.outcome:
            closed = svc.dispatch.close(act.order_id, act.outcome)
            if closed:
                svc.notify_outcome(closed["case_id"], act.outcome)
            return {"ok": bool(closed)}
        raise HTTPException(400, "bad action")

    # -------------------------------------------------------------- static --
    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
