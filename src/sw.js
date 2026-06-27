// L4 — Service Worker for asset caching
var CACHE_NAME = 'bayan-v1';
var STATIC_ASSETS = [
  '/',
  '/css/tokens.css',
  '/css/base.css',
  '/css/components.css',
  '/css/tailwind-output.css',
  '/js/app.js',
  '/js/editor.js',
  '/js/renderer.js',
  '/js/selection.js',
  '/js/ui.js',
  '/js/dialogs.js',
  '/js/theme.js',
  '/js/format.js',
  '/js/autocomplete.js',
  '/js/analytics.js',
  '/js/documents/doc-utils.js',
  '/js/documents/import.js',
  '/js/documents/export.js',
  '/js/documents/documents.js',
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
    caches.match(event.request).then(function(cached) {
      if (cached) return cached;
      return fetch(event.request).then(function(response) {
        if (response.ok && event.request.method === 'GET') {
          var clone = response.clone();
          caches.open(CACHE_NAME).then(function(cache) {
            cache.put(event.request, clone);
          });
        }
        return response;
      });
    })
  );
});
