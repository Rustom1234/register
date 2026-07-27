"""Self-narrating demo recorder. Run the seeded server first
(`make demo`), then `python scripts/record_demo.py` — the video lands in
docs/ (override with PUKAAR_VIDEO_DIR). On a normal connection the map
records with real CARTO tiles.
"""
import os
from playwright.sync_api import sync_playwright

OUT = os.environ.get("PUKAAR_VIDEO_DIR", "docs")
os.makedirs(OUT, exist_ok=True)
proxy = os.environ.get("HTTPS_PROXY")

OVERLAY = """
(() => {
  const cur = document.createElement('div');
  cur.id = 'pk-cursor';
  cur.style.cssText = 'position:fixed;width:20px;height:20px;border-radius:50%;' +
    'border:2.5px solid #fff;background:rgba(255,255,255,0.28);z-index:999999;' +
    'pointer-events:none;transform:translate(-50%,-50%);left:-40px;top:-40px;' +
    'box-shadow:0 0 8px rgba(0,0,0,0.7);transition:left .05s linear, top .05s linear';
  const cap = document.createElement('div');
  cap.id = 'pk-cap';
  cap.style.cssText = 'position:fixed;left:50%;bottom:64px;transform:translateX(-50%);' +
    'background:rgba(10,12,16,0.92);color:#fff;padding:11px 22px;border-radius:999px;' +
    'font:600 16px system-ui;z-index:999998;border:1px solid rgba(255,255,255,0.22);' +
    'max-width:80%;text-align:center;opacity:0;transition:opacity .35s';
  document.addEventListener('DOMContentLoaded', () => {
    document.body.appendChild(cur); document.body.appendChild(cap);
  });
  if (document.body) { document.body.appendChild(cur); document.body.appendChild(cap); }
  document.addEventListener('mousemove', e => {
    cur.style.left = e.clientX + 'px'; cur.style.top = e.clientY + 'px';
  }, true);
  document.addEventListener('mousedown', () => {
    cur.style.background = 'rgba(250,178,25,0.75)';
    setTimeout(() => cur.style.background = 'rgba(255,255,255,0.28)', 220);
  }, true);
})();
"""

def main():
    with sync_playwright() as p:
        exe = os.environ.get("PUKAAR_PW_EXEC")   # unset locally: playwright's own chromium
        browser = p.chromium.launch(
            executable_path=exe,
            proxy={"server": proxy, "bypass": "localhost,127.0.0.1"} if os.environ.get("PUKAAR_PW_PROXY") else None)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=OUT, record_video_size={"width": 1280, "height": 800},
            ignore_https_errors=True)
        page = ctx.new_page()
        page.add_init_script(OVERLAY)

        def cap(text, hold=0):
            page.evaluate(
                "t => { const c = document.getElementById('pk-cap');"
                "if (c) { c.textContent = t; c.style.opacity = t ? 1 : 0; } }", text)
            if hold:
                page.wait_for_timeout(hold)

        def glide_click(selector=None, xy=None, settle=350):
            if selector:
                el = page.locator(selector).first
                el.scroll_into_view_if_needed()
                box = el.bounding_box()
                x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            else:
                x, y = xy
            page.mouse.move(x, y, steps=22)
            page.wait_for_timeout(settle)
            page.mouse.click(x, y)

        page.goto("http://localhost:8877/", wait_until="domcontentloaded")
        page.wait_for_timeout(3500)
        cap("PUKAAR — a live street-aid control room · Nizamuddin, Delhi (simulated city, real pipeline)", 3800)

        # ---- witness reports in English
        cap("A witness sees someone in need and messages the aid line — in English…")
        glide_click("#msg-in")
        page.keyboard.type("An injured man is sitting under the flyover, his bandage is soaked", delay=26)
        page.wait_for_timeout(350)
        page.keyboard.press("Enter")
        page.wait_for_timeout(2600)

        cap("…the agent answers in the witness's own language, and asks for a location")
        glide_click(xy=(830, 430))                       # drop the 📍 witness pin on the map
        page.wait_for_timeout(500)
        glide_click("#btn-loc")
        page.wait_for_timeout(2400)

        cap("A photo of the surroundings — pick a scene, no face needed")
        glide_click("#btn-photo")
        page.wait_for_timeout(1200)
        glide_click("#photo-menu button[data-hint]")   # wound + soaked bandage
        page.wait_for_timeout(1600)
        try:
            glide_click("#quick button")
        except Exception:
            pass
        cap("Report filed. Four steps, under ninety seconds.", 2600)

        # ---- golden run
        cap("🎬 A P1 medical case — watch the whole arc. The camera follows the responder.")
        glide_click('button[data-sc="golden_run"]')
        page.select_option("#speed", "30")
        page.wait_for_timeout(6500)
        cap("Parallel offers to the nearest trusted responders — first accept wins (GoodSAM pattern)", 6000)
        cap("Accepted. En route — dashed line, live trail, clinical flag on board.", 6000)
        cap("On site: wound dressed, kit given, clinical team called in.", 5000)
        cap("And the witness is never left wondering: worker en route → reached → served, live in their chat", 5000)

        # ---- case detail
        rows = page.locator(".case-row")
        if rows.count():
            cap("Every case: DIGIPIN (India Post 4m geocode), witnesses, kit, HMAC provenance, timeline")
            glide_click(".case-row")
            page.wait_for_timeout(4200)
            glide_click("#detail-close")

        # ---- privacy heatmap
        cap("And 90 days later? Only this survives the purge: coarse cells and counts — no pins, no photos, no people")
        glide_click("#cells-toggle")
        page.wait_for_timeout(5200)
        glide_click("#cells-toggle")

        # ---- dedup
        cap("Three witnesses report the same man…")
        glide_click('button[data-sc="duplicate_burst"]')
        page.wait_for_timeout(2500)
        cap("…one case, one kit — deduplicated by place and time", 3200)

        # ---- emergency gate
        cap("And if it's a real emergency?")
        glide_click("#msg-in")
        page.keyboard.type("ek aadmi behosh pada hai sadak par!!", delay=24)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1500)
        cap("Fixed 112 reply — no model ever speaks in the emergency path. Tested at 100% recall.", 4200)

        # ---- the responder's side: /responder in a phone frame over the map
        cap("The other side of the marketplace: the responder app — /responder on any phone")
        page.evaluate(
            "() => { const f = document.createElement('iframe');"
            "f.id = 'pk-phone'; f.src = '/responder';"
            "f.style.cssText = 'position:fixed;right:18px;top:64px;width:372px;height:700px;"
            "z-index:999997;border:10px solid #23262e;border-radius:26px;background:#0d0d0d;"
            "box-shadow:0 18px 60px rgba(0,0,0,0.65)';"
            "document.body.appendChild(f); }")
        phone = page.frame_locator("#pk-phone")
        phone.locator("#duty-btn").wait_for(timeout=15000)
        # duty on as an idle responder, then pin a fresh case ~500 m from them.
        # Every responder goes manual for this segment so a sim responder can't
        # win the parallel-offer race before the on-camera ACCEPT.
        rid = page.evaluate(
            "async () => { const s = await (await fetch('/api/state')).json();"
            "const post = (b) => fetch('/api/manual', {method: 'POST',"
            "  headers: {'content-type': 'application/json'}, body: JSON.stringify(b)});"
            "for (const r of s.sim.responders) await post({responder_id: r.id, manual: true});"
            "const idle = s.sim.responders.find(r => r.state === 'idle');"
            "return idle ? idle.id : 'resp_1'; }")
        phone.locator("#pick").select_option(rid)
        phone.locator("#duty-btn").click()
        page.wait_for_timeout(900)
        page.evaluate(
            "async (rid) => { const s = await (await fetch('/api/state')).json();"
            "const me = s.sim.responders.find(r => r.id === rid);"
            "const lat = me.lat + 350/111320,"
            "      lng = me.lng + 350/(111320*Math.cos(me.lat*Math.PI/180));"
            "const post = (u, b) => fetch(u, {method: 'POST',"
            "  headers: {'content-type': 'application/json'}, body: JSON.stringify(b)});"
            "await post('/api/wa/inbound', {phone: '+91-FIELD', kind: 'text',"
            "  text: 'ek aadmi ghayal hai, pair se khoon nikal raha hai'});"
            "await post('/api/wa/inbound', {phone: '+91-FIELD', kind: 'location', lat, lng});"
            "await post('/api/wa/inbound', {phone: '+91-FIELD', kind: 'button', text: 'fresh:10'});"
            "}", rid)
        cap("A witness pins a case nearby… the offer ping lands: kit, distance, DIGIPIN, countdown")
        offer = phone.locator('.offer:has-text("Medical kit")').locator("[data-acc]").first
        offer.wait_for(timeout=60000)
        page.wait_for_timeout(1400)
        offer.click()
        phone.locator(".banner.enroute").wait_for(timeout=20000)
        cap("ACCEPT — and the same responder starts moving on the map behind", 3000)
        phone.locator(".banner.onsite").wait_for(timeout=90000)
        cap("At the pin: kit checklist done, outcome recorded — the witness gets the closure message", 1600)
        phone.locator('[data-out="served"]').click()
        page.wait_for_timeout(2600)
        page.evaluate("() => document.getElementById('pk-phone').remove()")
        page.evaluate(   # hand everyone back to the sim
            "async () => { const s = await (await fetch('/api/state')).json();"
            "const post = (b) => fetch('/api/manual', {method: 'POST',"
            "  headers: {'content-type': 'application/json'}, body: JSON.stringify(b)});"
            "for (const r of s.sim.responders) await post({responder_id: r.id, manual: false}); }")

        # ---- metrics
        page.goto("http://localhost:8877/static/metrics.html", wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        cap("Pre-registered kill criteria, evaluated live — if Pukaar stops earning its numbers, it says so", 5000)

        # ---- close
        page.goto("http://localhost:8877/", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        cap("Witness → verify → deliver → care. 103 tests. No cameras. No database of the poor.", 5200)
        cap("PUKAAR · पुकार — the call", 3000)

        video = page.video
        ctx.close()
        print("video saved:", video.path())
        browser.close()

main()
