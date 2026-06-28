// L4 — Service Worker for asset caching
var CACHE_NAME = 'bayan-v3';
var STATIC_ASSETS = [
  '/',
  '/css/tokens.css',
  '/css/base.css',
  '/css/components.css',
  '/css/tailwind-output.css',
  '/js/bayan.bundle.js',
  '/favicon.svg',
];

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(STATIC_ASSETS);
    })
  );
});

self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(k) { return k !== CACHE_NAME; })
            .map(function(k) { return caches.delete(k); })
      );
    })
  );
});

self.addEventListener('fetch', function(event) {
  var url = new URL(event.request.url);
  if (url.pathname.startsWith('/api/')) return;

  event.respondWith(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.match(event.request).then(function(cached) {
        var fetchPromise = fetch(event.request).then(function(response) {
          if (response.ok && event.request.method === 'GET') {
            cache.put(event.request, response.clone());
          }
          return response;
        }).catch(function() { return cached; });
        return cached || fetchPromise;
      });
    })
  );
});
