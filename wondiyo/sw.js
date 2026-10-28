/* Wondiyo service worker — "once ag, olmazsa onbellek".
   Amac: sayfayi her acista GitHub Pages'ten TAZE cekmek, boylece yeni
   buton/duzeltme eklendiginde telefondaki kopya eskide kalmasin.
   Internet yoksa son basarili kopya gosterilir.
   GitHub API istekleri (baska origin) hic dokunulmadan gecer. */
const KOVA = "wondiyo";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  let u;
  try { u = new URL(e.request.url); } catch { return; }
  if (u.origin !== self.location.origin) return;   // api.github.com'a karisma

  e.respondWith(
    fetch(e.request)
      .then((y) => {
        if (y && y.ok) {
          const kopya = y.clone();
          caches.open(KOVA).then((c) => c.put(e.request, kopya)).catch(() => {});
        }
        return y;
      })
      .catch(() => caches.match(e.request).then((y) => y || Response.error()))
  );
});
