"""FastAPI app — serves the demo control room and the (simulated) WhatsApp line.

Single process: a 1s background loop advances the sim clock, the dispatch
engine, and a periodic retention purge. The UI polls /api/state.
"""

import asyncio
import pathlib
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .whatsapp import CloudApi, parse_webhook

from . import strings
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
    action: str            # accept | decline | outcome | assign
    assignment_id: str | None = None
    order_id: str | None = None
    outcome: str | None = None
    responder_id: str | None = None


class ManualCtl(BaseModel):
    responder_id: str
    manual: bool


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
            "script": svc.script,
            "prov_ephemeral": svc.prov.ephemeral,
            "zone": {"lat": cfg.zone_lat, "lng": cfg.zone_lng, "radius_m": cfg.zone_radius_m},
            "sim": sim.snapshot(),
            "cases": cases,
            "orders": orders,
            "assignments": svc.store.query(
                "SELECT * FROM assignments ORDER BY offered_at DESC LIMIT 40"),
            "feed": list(svc.feed)[-45:][::-1],
            "metrics": svc.metrics(),
            "instructions": strings.INSTRUCTIONS,
            "kit_skus": strings.KIT_SKUS,
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
                if act.outcome == "escalated":
                    sim._pending_escalations[act.order_id] = sim.sim_now + 900
            return {"ok": bool(closed)}
        if act.action == "assign" and act.order_id and act.responder_id:
            return {"ok": svc.dispatch.manual_assign(act.order_id, act.responder_id)}
        raise HTTPException(400, "bad action")

    class ScriptCtl(BaseModel):
        script: str            # latin | deva

    @app.post("/api/script")
    def script_ctl(ctl: ScriptCtl):
        if ctl.script not in ("latin", "deva"):
            raise HTTPException(400, "script must be latin or deva")
        svc.script = ctl.script
        return {"script": svc.script}

    @app.post("/api/manual")
    def manual_ctl(ctl: ManualCtl):
        if ctl.manual:
            sim.manual.add(ctl.responder_id)
        else:
            sim.manual.discard(ctl.responder_id)
        return {"manual": sorted(sim.manual)}

    @app.get("/api/metrics/daily")
    def metrics_daily():
        return svc.daily_metrics()

    @app.get("/api/export")
    def export():
        return {
            "exported_at_sim": sim.sim_now,
            "cases": svc.store.query("SELECT * FROM cases"),
            "orders": svc.store.query("SELECT * FROM orders"),
            "assignments": svc.store.query("SELECT * FROM assignments"),
            "outcomes": svc.store.query("SELECT * FROM outcomes"),
            "audit_log": svc.store.query("SELECT * FROM audit_log ORDER BY ts"),
            "feed": list(svc.feed),
            "metrics": svc.metrics(),
            "daily": svc.daily_metrics(),
        }

    # ----------------------------------------------- WhatsApp Cloud API ---
    # Dormant until WA_TOKEN/WA_PHONE_ID exist; the webhook shape is live
    # and tested so P1 onboarding is config, not code.
    cloud = CloudApi()

    @app.get("/webhook")
    def wa_verify(request: Request):
        params = request.query_params
        if (params.get("hub.mode") == "subscribe"
                and params.get("hub.verify_token") == cloud.verify_token):
            return PlainTextResponse(params.get("hub.challenge", ""))
        raise HTTPException(403, "verification failed")

    @app.post("/webhook")
    async def wa_webhook(request: Request):
        payload = await request.json()
        handled = 0
        for m in parse_webhook(payload):
            if m["kind"] == "voice":
                # Voice notes: media download + STT is a P1 task (Sarvam
                # bake-off); acknowledge without pretending to understand.
                replies = svc.wa_inbound(m["phone"], "text", text="(voice note)")
            else:
                replies = svc.wa_inbound(m["phone"], m["kind"], text=m.get("text"),
                                         lat=m.get("lat"), lng=m.get("lng"),
                                         photo_hint=m.get("photo_hint"))
            handled += 1
            if cloud.configured:
                for r in replies:
                    cloud.reply(m["phone"], r)
        return {"handled": handled, "sending": cloud.configured}

    # -------------------------------------------------------------- static --
    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
