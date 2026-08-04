"""FastAPI app — serves the demo control room and the (simulated) WhatsApp line.

Single process: a 1s background loop advances the sim clock, the dispatch
engine, and a periodic retention purge. The UI polls /api/state.
"""

import asyncio
import os
import pathlib
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .report import render_report
from .whatsapp import CloudApi, parse_webhook, verify_signature

from . import geo, strings
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
    # In-memory by default; PUKAAR_DB=<path> persists the demo across restarts.
    store = Store(cfg.db_path) if os.environ.get("PUKAAR_DB") else Store(":memory:")
    holder: dict = {}
    svc = PukaarService(cfg, store, now_fn=lambda: holder["sim"].sim_now if "sim" in holder else 0.0)
    sim = Sim(svc, cfg)
    holder["sim"] = sim
    if os.environ.get("PUKAAR_SEED_DEMO"):
        sim.seed_demo()

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
            try:
                sim.tick(now - last)
                if sim.sim_now - last_purge > 6 * 3600:  # purge every 6 sim-hours
                    svc.run_purge()
                    last_purge = sim.sim_now
            except Exception:  # one bad tick must never freeze the demo
                import traceback
                traceback.print_exc()
            last = now

    app = FastAPI(title="Pukaar demo", lifespan=lifespan)
    app.state.svc, app.state.sim = svc, sim

    # ---- staff gate (hosted deploys) -----------------------------------
    # With PUKAAR_ADMIN_TOKEN set, everything is staff-only EXCEPT the
    # witness-facing webhooks and the health probe: a hosted control room
    # must never expose live witness chats, pins, or exports to the open
    # internet. /login?token=... sets the cookie so all pages just work.
    OPEN_PATHS = {"/health", "/api/wa/inbound", "/webhook", "/login",
                  "/favicon.ico"}

    @app.middleware("http")
    async def staff_gate(request: Request, call_next):
        token = cfg.admin_token
        if token:
            path = request.url.path
            if path not in OPEN_PATHS:
                ok = (request.cookies.get("wayside_staff") == token
                      or request.headers.get("x-wayside-token") == token)
                if not ok:
                    return PlainTextResponse(
                        "Wayside staff access required. Open /login?token=<your token> once "
                        "on this device (ask the coordinator for the token).",
                        status_code=401)
        return await call_next(request)

    @app.get("/login")
    def login(token: str = ""):
        if not cfg.admin_token or token != cfg.admin_token:
            raise HTTPException(401, "wrong or missing token")
        from fastapi.responses import RedirectResponse
        resp = RedirectResponse("/", status_code=302)
        resp.set_cookie("wayside_staff", token, httponly=True, samesite="lax",
                        max_age=60 * 60 * 24 * 30)
        return resp

    def _cells() -> list[dict]:
        # 90-day aggregate cells with map bounds — the only location data
        # that survives the purge, rendered as the privacy-story heatmap.
        out = []
        for row in svc.store.query("SELECT * FROM analytics_cells"):
            b = geo.cell_bounds(row["cell"])
            if b:
                out.append({**row, "south": b[0], "west": b[1],
                            "north": b[2], "east": b[3]})
        return out

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
            "depots": sim.depots(),
            "cases": cases,
            "orders": orders,
            "assignments": svc.store.query(
                "SELECT * FROM assignments ORDER BY offered_at DESC LIMIT 40"),
            "feed": list(svc.feed)[-45:][::-1],
            "metrics": svc.metrics(),
            "instructions": strings.INSTRUCTIONS,
            "kit_skus": strings.KIT_SKUS,
            "config": {"offer_ttl_s": cfg.offer_ttl_s},
            "cells": _cells(),
            # Last 6 conversations, with the interactive demo phone always
            # pinned (busy sessions must never push it out of the window).
            "conversations": {
                phone: conv.log[-30:]
                for phone, conv in (
                    ([("+91-DEMO", svc.conversations["+91-DEMO"])] if "+91-DEMO" in svc.conversations else [])
                    + [(p, c) for p, c in list(svc.conversations.items())[-6:] if p != "+91-DEMO"]
                )
            },
        }

    # ---------------------------------------------------------- scenarios --
    @app.post("/api/scenario/{name}")
    def scenario(name: str):
        if name not in SCENARIOS:
            raise HTTPException(404, f"unknown scenario: {name}")
        sim.last_scenario_phone = None
        result = sim.run_scenario(name)
        # The phone panel jumps to the spawned thread so the story plays
        # on-screen instead of in a conversation nobody is looking at.
        return {"result": result, "phone": getattr(sim, "last_scenario_phone", None)}

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
            if act.outcome not in ("served", "escalated", "not_found", "declined"):
                raise HTTPException(400, "outcome must be served|escalated|not_found|declined")
            closed = svc.dispatch.close(act.order_id, act.outcome)
            if closed:
                # Human closes settle the kit ledger through the same rail
                # the sim uses — depot stock and restocks stay truthful.
                sim.settle_kit(act.order_id, act.outcome)
                svc.notify_outcome(closed["case_id"], act.outcome)
                if act.outcome == "escalated":
                    sim._pending_escalations[act.order_id] = sim.sim_now + 900
            return {"ok": bool(closed)}
        if act.action == "arrived" and act.order_id:
            # geolocation-free fallback: the responder taps "I've arrived"
            svc.dispatch.arrived(act.order_id)
            return {"ok": True}
        if act.action == "assign" and act.order_id and act.responder_id:
            return {"ok": svc.dispatch.manual_assign(act.order_id, act.responder_id)}
        if act.action == "sos" and act.responder_id:
            # Rider safety: one tap reaches the coordinator, loudly.
            name = next((r["name"] for r in sim.snapshot()["responders"]
                         if r["id"] == act.responder_id), act.responder_id)
            svc.emit("sos", {"responder_id": act.responder_id, "name": name})
            return {"ok": True}
        raise HTTPException(400, "bad action")

    class PushSub(BaseModel):
        responder_id: str
        subscription: dict

    @app.get("/api/push/vapid")
    def push_vapid():
        return {"key": svc.push.vapid_public_key()}

    @app.post("/api/push/subscribe")
    def push_subscribe(body: PushSub):
        svc.push.subscribe(body.responder_id, body.subscription)
        return {"ok": True}

    class PinReq(BaseModel):
        case_id: str

    @app.post("/api/coordinator/request_pin")
    def request_pin(body: PinReq):
        return {"ok": svc.request_pin(body.case_id)}

    class ScriptCtl(BaseModel):
        script: str            # auto | en | hinglish | deva  (latin = hinglish alias)

    @app.post("/api/script")
    def script_ctl(ctl: ScriptCtl):
        value = "hinglish" if ctl.script == "latin" else ctl.script
        if value not in ("auto", "en", "hinglish", "deva"):
            raise HTTPException(400, "script must be auto|en|hinglish|deva")
        svc.script = value
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

    @app.get("/health")
    def health():
        # tick_age_s is the watchdog signal: an external pinger alerting on
        # age > ~10s catches a dead tick loop even while HTTP still serves.
        return {"ok": True, "backend": svc.backend.name, "sim_now": sim.sim_now,
                "tick_age_s": round(time.monotonic() - sim.last_tick_real, 1),
                "cases": len(svc.store.query("SELECT id FROM cases"))}

    @app.get("/report", response_class=HTMLResponse)
    def session_report():
        return render_report(svc, sim)

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
            "cells": _cells(),
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
        raw = await request.body()
        if not verify_signature(raw, request.headers.get("X-Hub-Signature-256"),
                                cloud.app_secret):
            raise HTTPException(403, "bad signature")
        payload = await request.json()
        handled = 0
        for m in parse_webhook(payload):
            if m["kind"] == "voice":
                # Voice notes over the real transport: STT (Sarvam bake-off)
                # is the P1 task — until then the note flows as an empty
                # transcript, keeps the mic bubble semantics, and the intake
                # asks for the missing pieces instead of pretending to hear.
                replies = svc.wa_inbound(m["phone"], "voice", text=None)
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

    @app.get("/responder")
    def responder_app():
        return FileResponse(STATIC / "responder.html")

    @app.get("/witness")
    def witness_app():
        return FileResponse(STATIC / "witness.html")

    @app.get("/supervisor")
    def supervisor_app():
        return FileResponse(STATIC / "supervisor.html")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        # Browsers request this unprompted on every surface (including the
        # bare /login page) — serve the app icon instead of a 404.
        return FileResponse(STATIC / "icons" / "icon-192.png",
                            media_type="image/png")

    @app.get("/sw.js")
    def service_worker():
        # Served at the root so its scope covers /responder — a worker
        # registered from /static/ could only ever control /static/.
        return FileResponse(STATIC / "sw.js", media_type="text/javascript")

    @app.get("/data/demo_zone.geojson")
    def zone_geojson():
        # The basemap and the router read the same file — the streets you
        # see are exactly the streets riders are routed on.
        return FileResponse(STATIC.parent / "data" / "demo_zone.geojson",
                            media_type="application/geo+json")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
