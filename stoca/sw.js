// Web Wallet - service worker (offline-first)
// Cambia il numero di versione ad ogni modifica ai file per forzare l'aggiornamento.
const CACHE_NAME = 'wallet-v4';

const CORE_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './libs/Sortable.min.js',
  './libs/JsBarcode.all.min.js',
  './libs/qrcode.min.js',
  './libs/html5-qrcode.min.js',
  './libs/html2canvas.min.js'
];

const OPTIONAL_ASSETS = [
  './logos/icon-192.png',
  './logos/icon-512.png'
];

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    await cache.addAll(CORE_ASSETS);
    // Le icone non devono bloccare l'installazione se mancano
    await Promise.all(OPTIONAL_ASSETS.map(url => cache.add(url).catch(() => {})));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // niente da gestire fuori dal sito

  event.respondWith((async () => {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(req, { ignoreSearch: true });

    // Aggiornamento in background: la prossima apertura avrà la versione nuova
    const refresh = fetch(req).then(res => {
      if (res && res.status === 200) cache.put(req, res.clone());
      return res;
    }).catch(() => null);

    if (cached) {
      event.waitUntil(refresh);
      return cached; // risposta immediata dalla cache, senza aspettare la rete
    }

    const res = await refresh;
    if (res) return res;

    // Navigazione senza cache e senza rete: apri comunque l'app
    if (req.mode === 'navigate') {
      const fallback = await cache.match('./index.html');
      if (fallback) return fallback;
    }
    return new Response('Offline', { status: 503, statusText: 'Offline' });
  })());
});
