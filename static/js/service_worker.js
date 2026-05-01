const CACHE_NAME = 'yasmimos-v3-outfit';
const urlsToCache = [
  '/',
  '/static/css/style.css',
  '/static/js/main.js'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request).catch(() => {
        return caches.match(event.request);
    })
  );
});
