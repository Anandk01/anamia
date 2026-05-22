const CACHE_NAME = 'anemia-care-v1';
const STATIC_ASSETS = ['/', '/index.html'];
self.addEventListener('install', e => e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(STATIC_ASSETS))));
self.addEventListener('fetch', e => { if (e.request.url.includes('/api/')) return; e.respondWith(caches.match(e.request).then(r => r || fetch(e.request))); });
