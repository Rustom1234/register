/* Wayside responder service worker — installable app, push to the lock
   screen, and an offline shell: a rider in a dead-signal underpass can
   still open the app, see their active order screen, and read the kit
   checklist. Live data stays network-first — stale dispatch info is
   worse than a spinner — but the shell itself never 404s offline. */
"use strict";

const CACHE = "wayside-20260804p";
const SHELL = [
  "/responder",
  "/static/responder.js?v=20260804p",
  "/static/manifest.webmanifest",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  // witness shell: a reporter with no signal still gets the page (with an
  // honest "didn't send" state) instead of the browser's dinosaur
  "/witness",
  "/static/witness.js?v=20260804p",
  "/static/app.css?v=20260804p",
  "/static/basemap.js?v=20260804p",
  "/static/vendor/maplibre-gl.js?v=20260804p",
  "/static/vendor/maplibre-gl.css?v=20260804p",
  "/data/demo_zone.geojson",
];

self.addEventListener("install", (e) => {
  // Resilient precache: a single 401/offline miss (e.g. staff gate before
  // the login cookie exists) must not brick install — push notifications
  // matter more than a complete shell.
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => Promise.allSettled(SHELL.map((u) => c.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;                    // never touch webhooks/API posts
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return;        // live data: network only

  // App navigations (rider + witness): freshest when online, shell when not.
  const navShell = url.pathname.startsWith("/responder") ? "/responder"
    : url.pathname.startsWith("/witness") ? "/witness" : null;
  if (req.mode === "navigate" && navShell) {
    e.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(navShell, copy));
          }
          return res;
        })
        .catch(() => caches.match(navShell))
    );
    return;
  }

  // The basemap's street data: fresh when online, cached offline (it is
  // also part of the precached shell so the witness map works airplane-mode).
  if (url.pathname === "/data/demo_zone.geojson") {
    e.respondWith(
      fetch(req).then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      }).catch(() => caches.match(req))
    );
    return;
  }

  // Static assets. This worker's scope is the whole origin (registered at
  // /sw.js so it can control /responder), which means it also intercepts
  // the control room's and witness page's assets — those must NEVER be
  // served stale. Only the precached shell is cache-first; everything else
  // is network-first with the cache as an offline fallback.
  if (url.pathname.startsWith("/static/")) {
    const inShell = SHELL.includes(url.pathname + url.search) || SHELL.includes(url.pathname);
    e.respondWith(
      inShell
        ? caches.match(req).then((hit) => hit || fetch(req).then((res) => {
            if (res.ok) {
              const copy = res.clone();
              caches.open(CACHE).then((c) => c.put(req, copy));
            }
            return res;
          }))
        : fetch(req).then((res) => {
            if (res.ok) {
              const copy = res.clone();
              caches.open(CACHE).then((c) => c.put(req, copy));
            }
            return res;
          }).catch(() => caches.match(req))
    );
  }
});

self.addEventListener("push", (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch { /* non-JSON push */ }
  e.waitUntil(self.registration.showNotification(d.title || "Wayside", {
    body: d.body || "New activity on your Wayside shift.",
    icon: "/static/icons/icon-192.png",
    badge: "/static/icons/icon-192.png",
    tag: d.tag || "wayside-offer",
    renotify: true,
    data: { url: d.url || "/responder" },
  }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "/responder";
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((ws) => {
    for (const w of ws) {
      if (w.url.includes("/responder") && "focus" in w) return w.focus();
    }
    return self.clients.openWindow(url);
  }));
});
