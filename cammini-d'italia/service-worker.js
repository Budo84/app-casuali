const CACHE_NAME = 'cammini-italia-v5';
const APP_SHELL = [
  './',
  './index.html',
  './manifest.json',
  './css/style.css',
  './js/app.js',
  './js/db.js',
  './js/gpx.js',
  './js/strutture.js',
  './js/geocode.js',
  './data/db.json',
  './icons/icon-192.png',
  './icons/icon-512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const req = event.request;

  // Le tile della mappa (OpenStreetMap) e le librerie CDN: rete prima, nessuna cache forzata
  if (req.url.includes('tile.openstreetmap.org') || req.url.includes('cdnjs.cloudflare.com') || req.url.includes('fonts.g')) {
    event.respondWith(
      fetch(req).catch(() => caches.match(req))
    );
    return;
  }

  // Ricerca strutture ricettive (Overpass API) e geocodifica inversa (Nominatim): sempre e solo rete, mai cache.
  // I dati cambiano nel tempo e i risultati vengono già salvati separatamente in localStorage
  // dal modulo js/strutture.js per la consultazione offline.
  if (req.url.includes('overpass-api.de') || req.url.includes('nominatim.openstreetmap.org')) {
    event.respondWith(fetch(req));
    return;
  }

  // App shell e dati locali: cache-first, così l'app parte anche offline
  event.respondWith(
    caches.match(req).then(cached => {
      if (cached) return cached;
      return fetch(req).then(res => {
        if (req.method === 'GET' && res.ok && req.url.startsWith(self.location.origin)) {
          const resClone = res.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(req, resClone));
        }
        return res;
      }).catch(() => cached);
    })
  );
});
