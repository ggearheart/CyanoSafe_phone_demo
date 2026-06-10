const CACHE = 'cyanosafe-v1';
const SHELL = [
  '/CyanoSafe_phone_demo/',
  '/CyanoSafe_phone_demo/index.html',
  '/CyanoSafe_phone_demo/waterboards-logo.png',
  '/CyanoSafe_phone_demo/icon-192.png',
  '/CyanoSafe_phone_demo/icon-512.png',
  '/CyanoSafe_phone_demo/manifest.json',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js',
];

// Install: cache app shell
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

// Activate: clear old caches
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Fetch strategy:
// - blooms.json / wid_map.json: network-first (live data), fall back to cache
// - everything else: cache-first
self.addEventListener('fetch', e => {
  const url = e.request.url;
  if (url.includes('blooms.json') || url.includes('wid_map.json')) {
    e.respondWith(
      fetch(e.request)
        .then(res => {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
          return res;
        })
        .catch(() => caches.match(e.request))
    );
  } else {
    e.respondWith(
      caches.match(e.request).then(cached => cached || fetch(e.request).then(res => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      }))
    );
  }
});
