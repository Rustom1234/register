/* Wayside responder service worker — makes the responder page an
   installable app and carries push notifications to the lock screen.
   Kept deliberately thin: network-first (the app is a live dashboard,
   stale data is worse than a spinner), push + click handling only. */
"use strict";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

// A fetch handler must exist for some browsers to treat this as an app;
// passthrough keeps live data live.
self.addEventListener("fetch", () => {});

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
