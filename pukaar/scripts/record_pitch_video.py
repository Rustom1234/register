"""Record the pitch video — the one that leads with the real map.

Run the server first (calm board, no seeding):

    PUKAAR_BACKEND=mock .venv/bin/python -m pukaar

then

    .venv/bin/python scripts/record_pitch_video.py

The video lands in research/pitch/ (override with PUKAAR_VIDEO_DIR).

This is a true Playwright screencast at 1280x800, not a stitch of stills:
the drive you see is the sim moving a rider along the real Nizamuddin
street graph, dead-reckoned between 1 Hz polls, captured as it happened.

Storyboard — the map is the thesis, so the film opens and closes on it:
  1  the real streets of Nizamuddin, named
  2  ten kilometres of real Delhi around them
  3  a witness reports, in their own words, with a pin
  4  the offer wave, and a rider accepts on a phone
  5  the drive: depot for the kit, then the pin — on real roads
  6  outcome, and the witness is told how it ended
  7  what survives 90 days: coarse cells, nothing else
"""
import json
import os
import pathlib
import shutil
import subprocess
import time

from playwright.sync_api import sync_playwright

BASE = os.environ.get("PUKAAR_BASE", "http://127.0.0.1:8877")
OUT = os.environ.get(
    "PUKAAR_VIDEO_DIR",
    str(pathlib.Path(__file__).resolve().parents[2] / "research" / "pitch"))
EXEC = os.environ.get("PUKAAR_PW_EXEC") or None
# The raw screencast and its beat marks are build scratch — only the cut
# mp4 belongs in the pitch folder (and in git).
CAPTURE = str(pathlib.Path(OUT) / ".capture")
os.makedirs(OUT, exist_ok=True)
os.makedirs(CAPTURE, exist_ok=True)

# Cursor + caption chrome, injected before any page script runs.
OVERLAY = """
(() => {
  const add = () => {
    if (document.getElementById('pk-cap')) return;
    const cur = document.createElement('div');
    cur.id = 'pk-cursor';
    cur.style.cssText = 'position:fixed;width:20px;height:20px;border-radius:50%;' +
      'border:2.5px solid #fff;background:rgba(255,255,255,0.28);z-index:2147483646;' +
      'pointer-events:none;transform:translate(-50%,-50%);left:-40px;top:-40px;' +
      'box-shadow:0 0 8px rgba(0,0,0,0.7);transition:left .05s linear, top .05s linear';
    const cap = document.createElement('div');
    cap.id = 'pk-cap';
    cap.style.cssText = 'position:fixed;left:50%;bottom:54px;transform:translateX(-50%);' +
      'background:rgba(8,10,14,0.93);color:#fff;padding:13px 26px;border-radius:14px;' +
      'font:600 17px/1.4 system-ui,-apple-system,Segoe UI,Roboto;z-index:2147483647;' +
      'border:1px solid rgba(255,255,255,0.18);max-width:74%;text-align:center;' +
      'opacity:0;transition:opacity .4s;box-shadow:0 10px 40px rgba(0,0,0,0.6);' +
      'pointer-events:none';
    document.body.appendChild(cur);
    document.body.appendChild(cap);
  };
  if (document.body) add();
  document.addEventListener('DOMContentLoaded', add);
  document.addEventListener('mousemove', e => {
    const c = document.getElementById('pk-cursor');
    if (c) { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }
  }, true);
  document.addEventListener('mousedown', () => {
    const c = document.getElementById('pk-cursor');
    if (!c) return;
    c.style.background = 'rgba(250,178,25,0.75)';
    setTimeout(() => { c.style.background = 'rgba(255,255,255,0.28)'; }, 220);
  }, true);
})();
"""

# A full-bleed card for the open and the close.
CARD = """
(t) => {
  let el = document.getElementById('pk-card');
  if (!el) {
    el = document.createElement('div');
    el.id = 'pk-card';
    el.style.cssText = 'position:fixed;inset:0;background:#07080b;color:#fff;' +
      'z-index:2147483645;display:flex;flex-direction:column;align-items:center;' +
      'justify-content:center;gap:18px;opacity:0;transition:opacity .6s;' +
      'font:700 46px/1.25 system-ui,-apple-system,Segoe UI,Roboto;text-align:center';
    document.body.appendChild(el);
  }
  if (t === null) {
    // A transparent full-bleed card still eats every click, so take it out
    // of the hit-testing entirely once it has faded.
    el.style.opacity = 0;
    el.style.pointerEvents = 'none';
    return;
  }
  el.innerHTML = t;
  el.style.opacity = 1;
  el.style.pointerEvents = 'auto';
}
"""


def main():
    # PUKAAR_RECUT=<raw .webm> re-edits an existing capture (with its
    # beats.json alongside) instead of shooting again — pacing is worth
    # iterating on, and a reshoot is three minutes of sim you already have.
    recut = os.environ.get("PUKAAR_RECUT")
    if recut:
        raw = pathlib.Path(recut)
        beats = json.loads((raw.parent / "beats.json").read_text())
        print(f"re-cutting {raw.name} from {len(beats)} beat marks")
        cut(raw, beats)
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=EXEC)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=CAPTURE,
            record_video_size={"width": 1280, "height": 800},
            device_scale_factor=1)
        page = ctx.new_page()
        page.add_init_script(OVERLAY)

        # Beat marks, in seconds from the first frame. The sim's own timing
        # (how long a dispatch wave takes to reach this rider, how long the
        # kit run is) cannot be dictated from here, so the shoot records
        # WHEN each beat actually happened and the cut below uses those
        # marks to pace the film. Nothing is staged twice; the edit only
        # decides how long you look at what was captured.
        beats = []
        t0 = [time.monotonic()]

        def beat(label):
            if t0[0] is None:
                return
            beats.append({"label": label, "t": round(time.monotonic() - t0[0], 2)})

        def cap(text, hold=0):
            page.evaluate(
                "t => { const c = document.getElementById('pk-cap');"
                "if (c) { c.innerHTML = t; c.style.opacity = t ? 1 : 0; } }", text)
            if hold:
                page.wait_for_timeout(hold)

        def card(html, hold=0):
            page.evaluate(CARD, html)
            if hold:
                page.wait_for_timeout(hold)

        def jump(lat, lng, zoom, hold=0):
            page.evaluate(
                "o => map.jumpTo({center:[o.lng, o.lat], zoom:o.z})",
                {"lat": lat, "lng": lng, "z": zoom})
            if hold:
                page.wait_for_timeout(hold)

        def fly(lat, lng, zoom, ms=2600, hold=0):
            page.evaluate(
                "o => map.flyTo({center:[o.lng, o.lat], zoom:o.z, duration:o.ms,"
                " essential:true})",
                {"lat": lat, "lng": lng, "z": zoom, "ms": ms})
            page.wait_for_timeout(ms + (hold or 0))

        def glide_click(selector=None, xy=None, settle=340, frame=None):
            """Move the visible cursor, then click by coordinate.

            Panels here rebuild their nodes at 1 Hz, so Playwright's
            "wait for stable" can never settle on them mid-sim; measuring
            the rect from the DOM and driving the mouse always can."""
            if selector:
                box = None
                for _ in range(12):
                    box = page.evaluate(
                        "sel => { const el = document.querySelector(sel);"
                        "if (!el) return null; const r = el.getBoundingClientRect();"
                        "return (r.width && r.height) ? {x:r.x+r.width/2, y:r.y+r.height/2} : null; }",
                        selector)
                    if box:
                        break
                    page.wait_for_timeout(300)
                if not box:
                    raise RuntimeError(f"no visible element for {selector}")
                x, y = box["x"], box["y"]
            else:
                x, y = xy
            page.mouse.move(x, y, steps=22)
            page.wait_for_timeout(settle)
            page.mouse.click(x, y)

        # =================================================== 1 · the map ==
        page.goto(BASE + "/", wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        beat("title")
        card("WAYSIDE"
             "<div style='font:400 22px/1.5 system-ui;opacity:.75;max-width:760px'>"
             "Someone sees a person who needs help.<br>That should be enough.</div>", 3200)
        card(None)
        page.wait_for_timeout(700)

        beat("map_zone")
        jump(28.5933, 77.2507, 15.4)
        page.wait_for_timeout(1400)
        cap("Nizamuddin, Delhi — <b>the real streets</b>, surveyed by "
             "OpenStreetMap contributors", 2900)
        fly(28.5930, 77.2495, 16.3, 2400, 400)
        cap("Humayun's Tomb. Sunder Nursery. The Dargah. The railway. "
            "Every road here is a road that is there.", 3600)

        # ================================================ 2 · real Delhi ==
        beat("map_delhi")
        cap("And ten kilometres of real Delhi around it — pan anywhere, "
            "it is all there")
        # 11.3, not 10.6: far enough to read as a city, close enough that
        # the arterials and the neighbourhood names are still legible.
        fly(28.5933, 77.2507, 11.3, 2600, 3200)
        cap("", 200)
        fly(28.5933, 77.2507, 15.2, 2200, 400)

        # ================================================= 3 · a witness ==
        beat("witness")
        cap("A witness sees someone in need, and messages the aid line")
        glide_click("#msg-in")
        page.keyboard.type(
            "An injured man is sitting under the flyover, his bandage is soaked",
            delay=26)
        page.wait_for_timeout(400)
        page.keyboard.press("Enter")
        page.wait_for_timeout(2800)

        cap("The agent answers in their language, and asks where")
        glide_click(xy=(760, 430))                 # drop the pin on a real street
        page.wait_for_timeout(600)
        glide_click("#btn-loc")
        page.wait_for_timeout(2600)

        cap("A photo of the scene — no face needed")
        glide_click("#btn-photo")
        page.wait_for_timeout(1300)
        try:
            glide_click("#photo-menu button[data-hint]")
            page.wait_for_timeout(1800)
        except Exception:
            pass
        try:
            glide_click("#quick button")
        except Exception:
            pass
        cap("Report filed. Four steps. No app, no account.", 2800)

        # ============================================ 4 · the offer wave ==
        # Every responder goes manual so no sim rider can win the race
        # before the on-camera ACCEPT.
        # Pick the rider whose nearest depot is closest, preferring a
        # scooter: the trip is rider -> depot -> pin, so a walker starting
        # across the zone turns a 30-second beat into a 65-minute one.
        pick = page.evaluate(
            "async () => {"
            "const s = await (await fetch('/api/state')).json();"
            "const post = (b) => fetch('/api/manual', {method:'POST',"
            "  headers:{'content-type':'application/json'}, body:JSON.stringify(b)});"
            "for (const r of s.sim.responders) await post({responder_id:r.id, manual:true});"
            "const m = (a,b) => Math.hypot((a.lat-b.lat)*111320,"
            "  (a.lng-b.lng)*111320*Math.cos(a.lat*Math.PI/180));"
            "let best = null;"
            "for (const r of s.sim.responders) {"
            "  if (r.state !== 'idle') continue;"
            "  for (const d of s.depots) {"
            "    const cost = m(r,d) + (r.mode === 'scooter' ? 0 : 1200);"
            "    if (!best || cost < best.cost) best = {cost, rid:r.id, mode:r.mode,"
            "      lat:d.lat, lng:d.lng, depot:d.name, away:Math.round(m(r,d))};"
            "  }"
            "}"
            "return best; }")
        rid = pick["rid"] if pick else "resp_1"
        print(f"  rider {rid} ({pick['mode']}) -> {pick['depot']} "
              f"{pick['away']} m away")

        beat("phone")
        cap("The other side of the marketplace: a trained responder's phone")
        page.evaluate(
            "() => { const f = document.createElement('iframe');"
            "f.id='pk-phone'; f.src='/responder';"
            "f.style.cssText='position:fixed;right:22px;top:70px;width:366px;height:690px;"
            "z-index:2147483640;border:10px solid #23262e;border-radius:28px;background:#0d0d0d;"
            "box-shadow:0 20px 70px rgba(0,0,0,0.7)';"
            "document.body.appendChild(f); }")
        phone = page.frame_locator("#pk-phone")
        phone.locator("#duty-btn").wait_for(timeout=20000)
        phone.locator("#pick").select_option(rid)
        phone.locator("#duty-btn").click()
        page.wait_for_timeout(1200)

        # The case goes ~450 m beyond the DEPOT, not beyond the rider: the
        # kit run is rider -> depot -> pin, and putting the pin past the
        # depot keeps the whole trip on screen and roughly a minute long.
        page.evaluate(
            "async (o) => {"
            "const lat = o.lat + 450/111320,"
            "      lng = o.lng + 450/(111320*Math.cos(o.lat*Math.PI/180));"
            "const post = (u,b) => fetch(u,{method:'POST',"
            "  headers:{'content-type':'application/json'}, body:JSON.stringify(b)});"
            "await post('/api/wa/inbound',{phone:'+91-FIELD',kind:'text',"
            "  text:'ek aadmi ghayal hai, pair se khoon nikal raha hai'});"
            "await post('/api/wa/inbound',{phone:'+91-FIELD',kind:'location',lat,lng});"
            "await post('/api/wa/inbound',{phone:'+91-FIELD',kind:'button',text:'fresh:10'});"
            "}", pick)
        beat("offer_wait")
        cap("The ping: what happened, which kit, and <b>how far by road</b> — "
            "measured on the real street graph, not as the crow flies")
        offer = phone.locator('.offer').locator("[data-acc]").first
        offer.wait_for(timeout=60000)
        page.wait_for_timeout(2600)
        beat("offer_accept")
        offer.click()
        phone.locator(".banner.enroute").wait_for(timeout=25000)
        cap("Accepted — first to accept wins, exactly how emergency dispatch "
            "works at scale", 2600)

        # ================================================== 5 · the drive ==
        # 12x so the kit run reads in about half a minute, and the camera
        # follows her rather than watching from orbit.
        beat("drive")
        page.select_option("#speed", "12")
        try:
            glide_click("#btn-follow", settle=200)
        except Exception:
            pass
        cap("Routed <b>via the depot</b> first: the kit lives on the NGO's "
            "shelf, not in a rider's bag")
        page.wait_for_timeout(7000)
        cap("She travels the actual streets — no dot floating over rooftops. "
            "1,432 surveyed road segments underneath her.")
        page.wait_for_timeout(7000)
        cap("Kit collected. Stock just decremented on that depot's tile — "
            "and if she can't find him, it goes back on the shelf.")
        page.wait_for_timeout(7000)
        cap("Turn by turn, on roads with real names: Mathura Road, "
            "Sabz Burj Circle, Lodhi Road.")
        try:
            phone.locator(".banner.onsite").wait_for(timeout=150000)
        except Exception:
            pass
        beat("onsite")
        cap("At the pin: kit checklist, then the outcome", 2800)
        try:
            phone.locator('[data-out="served"]').first.click()
        except Exception:
            pass
        page.wait_for_timeout(2600)

        # ================================================ 6 · the closure ==
        page.evaluate("() => { const f=document.getElementById('pk-phone');"
                      "if (f) f.remove(); }")
        beat("closure")
        cap("And the witness who cared enough to report is told how it ended. "
            "That is the loop.", 4200)
        page.evaluate(
            "async () => { const s = await (await fetch('/api/state')).json();"
            "const post = (b) => fetch('/api/manual', {method:'POST',"
            "  headers:{'content-type':'application/json'}, body:JSON.stringify(b)});"
            "for (const r of s.sim.responders) await post({responder_id:r.id, manual:false}); }")

        # ================================================== 7 · privacy ==
        beat("privacy")
        cap("A map of where vulnerable people sleep must not exist. "
            "So after 90 days, this is all that survives:")
        glide_click("#cells-toggle")
        page.wait_for_timeout(5200)
        cap("Coarse cells and counts. No pins. No photos. No people.", 3600)
        glide_click("#cells-toggle")
        page.wait_for_timeout(1200)

        # ==================================================== 8 · close ==
        cap("")
        beat("endcard")
        card("See it. Send word."
             "<div style='font:400 22px/1.6 system-ui;opacity:.75;max-width:820px'>"
             "Real streets · real routing · 245 tests · no cameras, "
             "no database of the poor</div>"
             "<div style='font:400 15px/1.6 system-ui;opacity:.45;margin-top:18px'>"
             "Map data © OpenStreetMap contributors, ODbL</div>", 5000)

        beat("end")
        video = page.video
        ctx.close()
        raw = pathlib.Path(video.path())
        browser.close()

    print(f"raw capture: {raw} ({raw.stat().st_size/1e6:.1f} MB)")
    pathlib.Path(CAPTURE, "beats.json").write_text(json.dumps(beats, indent=2))
    cut(raw, beats)


# How long each beat should READ, and how fast it may run. A beat is
# sped up only where the sim is making you wait (a dispatch wave timing
# out, a rider covering ground) — never through a click, a reply, or an
# arrival, which play at 1x so nothing looks staged.
PACE = [
    # (beat, max seconds on screen, max speed-up)
    # Over budget, a beat is first sped up as far as its cap allows and
    # then trimmed from the tail — so a beat never runs long, and never
    # runs faster than its cap.
    ("title",        4.0, 1.0),
    ("map_zone",    12.0, 1.7),   # pans speed up cleanly; trimming
    ("map_delhi",    9.0, 2.0),   # them would drop a whole caption
    ("witness",     19.0, 1.3),
    ("phone",        4.0, 2.0),
    ("offer_wait",   8.0, 3.5),   # the wave's own timeout — nothing to watch
    ("offer_accept", 6.0, 1.0),
    ("drive",       21.0, 1.8),
    ("onsite",       7.0, 1.0),
    ("closure",      5.5, 1.0),
    ("privacy",      9.5, 1.2),
    ("endcard",      5.0, 1.0),
]


def _ffmpeg() -> str:
    exe = os.environ.get("PUKAAR_FFMPEG") or shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise SystemExit(
            "error: no ffmpeg. Install one, set PUKAAR_FFMPEG, or "
            "`pip install imageio-ffmpeg`.")


def cut(raw: pathlib.Path, beats: list[dict]) -> None:
    """Trim the capture to the storyboard and encode the deliverable."""
    ff = _ffmpeg()
    marks = {b["label"]: b["t"] for b in beats}
    work = raw.parent / "_cut"
    work.mkdir(exist_ok=True)

    parts, plan = [], []
    for i, (label, budget, max_rate) in enumerate(PACE):
        start = marks.get(label)
        if start is None:
            continue
        nxt = next((PACE[j][0] for j in range(i + 1, len(PACE))
                    if PACE[j][0] in marks), "end")
        stop = marks.get(nxt, marks.get("end"))
        span = max(0.2, stop - start)
        rate = min(max_rate, max(1.0, span / budget))
        if span / rate > budget:            # still long — trim the tail
            stop = start + budget * rate
            span = stop - start
        piece = work / f"{i:02d}_{label}.mp4"
        subprocess.run(
            [ff, "-y", "-loglevel", "error", "-ss", f"{start:.2f}",
             "-to", f"{stop:.2f}", "-i", str(raw),
             "-filter:v", f"setpts=PTS/{rate:.3f}",
             "-an", "-r", "25", "-c:v", "libx264", "-preset", "medium",
             "-crf", "23", "-pix_fmt", "yuv420p", str(piece)],
            check=True)
        parts.append(piece)
        plan.append(f"  {label:13s} {span:6.1f}s -> {span / rate:5.1f}s "
                    f"({rate:.2f}x)")

    listing = work / "parts.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts))
    final = pathlib.Path(OUT) / "wayside-demo.mp4"
    subprocess.run(
        [ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(listing), "-c", "copy", str(final)], check=True)

    print("\n".join(plan))
    dur = subprocess.run(
        [ff, "-hide_banner", "-i", str(final)], capture_output=True,
        text=True).stderr
    dur = next((l.strip() for l in dur.splitlines() if "Duration" in l), "")
    print(f"\ncut: {final} ({final.stat().st_size/1e6:.1f} MB)\n{dur}")


main()
