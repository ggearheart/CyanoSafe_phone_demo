const CACHE = 'cyanosafe-v3';
const DATA_CACHE = 'cyanosafe-data-v1';
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
      Promise.all(keys.filter(k => k !== CACHE && k !== DATA_CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Fetch strategy:
// - blooms.json / CKAN API: network-first, cache with timestamp on success, fall back to cache
// - index.html: network-first, fall back to cache
// - everything else: cache-first
self.addEventListener('fetch', e => {
  const url = e.request.url;
  const isData = url.includes('blooms.json') || url.includes('data.ca.gov');
  const isShell = url.includes('index.html') || url.endsWith('/CyanoSafe_phone_demo/') || url.includes('wid_map.json');

  if (isData) {
    e.respondWith(
      fetch(e.request.clone())
        .then(res => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(DATA_CACHE).then(c => {
              // Store response with fetch timestamp as a custom header via metadata key
              c.put(e.request, clone);
              c.put('cached-at', new Response(Date.now().toString()));
            });
          }
          return res;
        })
        .catch(async () => {
          const cached = await caches.match(e.request, {cacheName: DATA_CACHE});
          if (cached) {
            // Inject offline header so the app can show stale banner
            const body = await cached.clone().text();
            return new Response(body, {
              headers: {'Content-Type':'application/json','X-From-Cache':'true'}
            });
          }
          return new Response('[]', {headers:{'Content-Type':'application/json','X-From-Cache':'true'}});
        })
    );
  } else if (isShell) {
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

// Listen for messages from the app (e.g. get cached-at timestamp)
self.addEventListener('message', e => {
  if (e.data === 'get-cached-at') {
    caches.open(DATA_CACHE).then(c => c.match('cached-at')).then(r => {
      r ? r.text().then(ts => e.source.postMessage({type:'cached-at', ts:Number(ts)}))
        : e.source.postMessage({type:'cached-at', ts:null});
    });
  }
});
