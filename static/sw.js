const CACHE = 'skladpro-v1';
const OFFLINE_URL = '/offline';

const STATIC_ASSETS = [
  '/static/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  // Only handle GET requests to our own origin
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== location.origin && !e.request.url.includes('fonts.googleapis')) return;

  e.respondWith(
    fetch(e.request)
      .then(res => {
        // Cache successful HTML page responses
        if (res.ok && (e.request.headers.get('accept') || '').includes('text/html')) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      })
      .catch(() => {
        // Offline fallback: serve cached page if available
        return caches.match(e.request).then(cached => {
          if (cached) return cached;
          // For HTML navigation, show last cached dashboard
          if ((e.request.headers.get('accept') || '').includes('text/html')) {
            return caches.match('/dashboard');
          }
        });
      })
  );
});
