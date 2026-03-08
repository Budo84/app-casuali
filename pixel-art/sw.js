const CACHE_NAME = 'pixelart-final-v1';
const ASSETS = [
    './',
    './index.html',
    './manifest.json'
];

// Installazione: memorizza i file nella cache
self.addEventListener('install', (e) => {
    console.log('[SW] Installazione e caching');
    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS);
        })
    );
});

// Attivazione: pulisce vecchie cache
self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then((keyList) => {
            return Promise.all(keyList.map((key) => {
                if (key !== CACHE_NAME) {
                    console.log('[SW] Rimozione vecchia cache', key);
                    return caches.delete(key);
                }
            }));
        })
    );
    return self.clients.claim();
});

// Fetch: serve i file dalla cache se offline
self.addEventListener('fetch', (e) => {
    e.respondWith(
        caches.match(e.request).then((response) => {
            return response || fetch(e.request);
        })
    );
});
