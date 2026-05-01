// YasMimos Service Worker v2
const CACHE_NAME = 'yasmimos-v2';
const OFFLINE_URL = '/offline/'; // Now at root
const ASSETS = [
  OFFLINE_URL,
  '/static/img/logo.png',
  '/static/css/style.css',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // Attempt to cache all, but if one fails, don't break the whole SW
      // We do this by mapping each request to a catch()
      return Promise.all(
        ASSETS.map(url => {
            return cache.add(url).catch(err => console.error('Failed to cache:', url, err));
        })
      );
    })
  );
  self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
  // Only handle navigate requests (full page loads)
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match(OFFLINE_URL);
      })
    );
  }
});

self.addEventListener('push', function(event) {
    let data = {};
    if (event.data) {
        data = event.data.json();
    }
    
    const title = data.title || 'YasMimos';
    const options = {
        body: data.body || 'Nova atualização!',
        icon: data.icon || '/static/img/logo.png',
        badge: '/static/img/logo.png', // Small icon for notification bar
        vibrate: [200, 100, 200, 100, 200],
        tag: data.tag || 'simple-push-notification-tag',
        renotify: true,
        requireInteraction: true,  // Keeps it on screen
        data: data.url || '/'
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    
    // Focus or open window
    event.waitUntil(
        clients.matchAll({type: 'window'}).then(function(clientList) {
            // Check if open
            for (var i = 0; i < clientList.length; i++) {
                var client = clientList[i];
                if (client.url.includes(event.notification.data) && 'focus' in client)
                    return client.focus();
            }
            if (clients.openWindow)
                return clients.openWindow(event.notification.data);
        })
    );
});
