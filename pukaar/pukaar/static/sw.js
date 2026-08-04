/* Wayside responder service worker — installable app, push to the lock
   screen, and an offline shell: a rider in a dead-signal underpass can
   still open the app, see their active order screen, and read the kit
   checklist. Live data stays network-first — stale dispatch info is
   worse than a spinner — but the shell itself never 404s offline. */
"use strict";

const CACHE = "wayside-20260804b";
const SHELL = [
  "/responder",
  "/static/responder.js?v=20260804b",
  "/static/manifest.webmanifest",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
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

  // Rider app navigation: freshest when online, shell when not.
  if (req.mode === "navigate" && url.pathname.startsWith("/responder")) {
    e.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put("/responder", copy));
          }
          return res;
        })
        .catch(() => caches.match("/responder"))
    );
    return;
  }

  // Static assets: cache-first, backfill on miss.
  if (url.pathname.startsWith("/static/")) {
    e.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      }))
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
