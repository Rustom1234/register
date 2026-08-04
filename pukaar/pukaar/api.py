"""FastAPI app — serves the demo control room and the (simulated) WhatsApp line.

Single process: a 1s background loop advances the sim clock, the dispatch
engine, and a periodic retention purge. The UI polls /api/state.
"""

import asyncio
import math
import os
import pathlib
import re
import time
from collections import deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .report import render_report
from .whatsapp import CloudApi, parse_webhook, verify_signature

from . import gate, geo, strings
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
    # Idempotency: the witness app mints one id per logical message and
    # reuses it on retries — a send whose RESPONSE was lost must not file
    # the report twice when the outbox redelivers it.
    client_id: str | None = None


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
    OPEN_PATHS = {"/health", "/api/wa/inbound", "/api/wa/photo", "/webhook",
                  "/login", "/favicon.ico"}

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
    def login(request: Request, token: str = ""):
        if not cfg.admin_token or token != cfg.admin_token:
            raise HTTPException(401, "wrong or missing token")
        from fastapi.responses import RedirectResponse
        resp = RedirectResponse("/", status_code=302)
        # Secure whenever the client reached us over TLS (directly or via a
        # reverse proxy) — a staff cookie must not replay over plain http.
        https = (request.url.scheme == "https"
                 or request.headers.get("x-forwarded-proto", "") == "https")
        resp.set_cookie("wayside_staff", token, httponly=True, samesite="lax",
                        secure=https, max_age=60 * 60 * 24 * 30)
        return resp

    def _case_media() -> dict[str, list[str]]:
        # real uploaded photos per case ("media" placeholder = described photo)
        out: dict[str, list[str]] = {}
        for r in svc.store.query(
                "SELECT case_id, media_ref FROM reports WHERE media_ref IS NOT NULL "
                "AND media_ref != 'media' AND media_purged = 0 AND case_id IS NOT NULL"):
            out.setdefault(r["case_id"], []).append(r["media_ref"])
        return out

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
    # The service's rate limit is per-phone — but this endpoint is open to
    # the internet (witnesses can't log in) and the phone id comes from the
    # client, so a flood can mint a fresh "phone" per request and bypass it.
    # A global window caps that; emergency texts pass, same as the per-phone
    # budget (the gate's fixed reply is cheap and a life is not).
    PHONE_RE = re.compile(r"^[+0-9A-Za-z:_\-]{3,32}$")
    inbound_times: deque = deque()
    seen_cids: dict[tuple[str, str], float] = {}   # (phone, client_id) -> monotonic

    @app.post("/api/wa/inbound")
    def wa_inbound(msg: Inbound):
        if not PHONE_RE.match(msg.phone):
            raise HTTPException(422, "malformed phone id")
        cid_key = None
        if msg.client_id:
            now_m = time.monotonic()
            for k in [k for k, t in seen_cids.items() if now_m - t > 3600]:
                seen_cids.pop(k, None)
            cid_key = (msg.phone, msg.client_id[:64])
            if cid_key in seen_cids:
                # duplicate delivery of an already-filed message: succeed
                # quietly with no replies, so the client stops retrying
                return {"replies": []}
        for v in (msg.lat, msg.lng):
            if v is not None and not math.isfinite(v):
                raise HTTPException(422, "coordinates must be finite numbers")
        if ((msg.lat is not None and not -90 <= msg.lat <= 90)
                or (msg.lng is not None and not -180 <= msg.lng <= 180)):
            raise HTTPException(422, "coordinates out of range")
        if not (msg.kind == "text" and gate.is_emergency(msg.text)):
            now = time.monotonic()
            while inbound_times and now - inbound_times[0] > 10:
                inbound_times.popleft()
            if len(inbound_times) >= 30:
                raise HTTPException(429, "line is busy — please try again in a moment")
            inbound_times.append(now)
        replies = svc.wa_inbound(msg.phone, msg.kind, text=msg.text, lat=msg.lat,
                                 lng=msg.lng, photo_hint=msg.photo_hint)
        # Record the cid only AFTER the message is actually filed — a retry
        # of a 429'd or errored send must not be swallowed as a "duplicate".
        if cid_key:
            seen_cids[cid_key] = time.monotonic()
        return {"replies": [{"text": r.text, "buttons": r.buttons, "id": r.string_id} for r in replies]}

    # A real photo from a real phone. Open (witnesses can't log in), but
    # tightly bounded: image types only, 3 MB cap, same global flood window.
    MEDIA_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    MEDIA_DIR = pathlib.Path(cfg.media_dir)
    MEDIA_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]{1,48}\.(jpg|png|webp)$")

    @app.post("/api/wa/photo")
    async def wa_photo(phone: str = Form(...), caption: str = Form(""),
                       file: UploadFile = File(...)):
        if not PHONE_RE.match(phone):
            raise HTTPException(422, "malformed phone id")
        ext = MEDIA_TYPES.get((file.content_type or "").lower())
        if not ext:
            raise HTTPException(415, "photos only (jpeg / png / webp)")
        now = time.monotonic()
        while inbound_times and now - inbound_times[0] > 10:
            inbound_times.popleft()
        if len(inbound_times) >= 30:
            raise HTTPException(429, "line is busy — please try again in a moment")
        inbound_times.append(now)
        data = await file.read()
        if len(data) > 3 * 1024 * 1024:
            raise HTTPException(413, "photo too large — 3 MB max")
        if not data:
            raise HTTPException(422, "empty file")
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        from .db import new_id
        ref = f"{new_id('med')}.{ext}"
        (MEDIA_DIR / ref).write_bytes(data)
        hint = (caption or "").strip()[:200] or "photo uploaded by the witness (unreviewed)"
        replies = svc.wa_inbound(phone, "photo", photo_hint=hint, media_ref=ref)
        return {"stored": ref,
                "replies": [{"text": r.text, "buttons": r.buttons, "id": r.string_id} for r in replies]}

    @app.get("/api/media/{name}")
    def media(name: str):
        # staff-gated by the middleware (not in OPEN_PATHS): witnesses upload,
        # only the ops room views. Strict name check kills traversal.
        if not MEDIA_NAME_RE.match(name):
            raise HTTPException(404, "no such media")
        p = MEDIA_DIR / name
        if not p.is_file():
            raise HTTPException(404, "no such media (purged or never existed)")
        return FileResponse(p)

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
            "restocks": sim.restocks_view(),
            "media": _case_media(),
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
    def health(request: Request):
        # tick_age_s is the watchdog signal: an external pinger alerting on
        # age > ~10s catches a dead tick loop even while HTTP still serves.
        # On a token-protected deploy the open probe answers ok/tick only —
        # backend name, sim clock and caseload are operational data.
        body = {"ok": True,
                "tick_age_s": round(time.monotonic() - sim.last_tick_real, 1)}
        staffed = (not cfg.admin_token
                   or request.cookies.get("wayside_staff") == cfg.admin_token
                   or request.headers.get("x-wayside-token") == cfg.admin_token)
        if staffed:
            body.update({"backend": svc.backend.name, "sim_now": sim.sim_now,
                         "cases": len(svc.store.query("SELECT id FROM cases"))})
        return body

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
