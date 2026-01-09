// Service Worker for AI Assistant PWA

const CACHE_NAME = 'ai-assistant-v1';
const STATIC_CACHE = 'ai-assistant-static-v1';

// Files to cache
const STATIC_FILES = [
    '/',
    '/static/mobile.html',
    '/static/styles.css',
    '/static/app.js',
    '/static/manifest.json',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('Service Worker installing...');
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            return cache.addAll(STATIC_FILES);
        })
    );
    self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('Service Worker activating...');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => {
                        return name !== CACHE_NAME && name !== STATIC_CACHE;
                    })
                    .map((name) => caches.delete(name))
            );
        })
    );
    return self.clients.claim();
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    
    // Skip API requests and WebSocket connections
    if (url.pathname.startsWith('/api/') || url.protocol === 'ws:' || url.protocol === 'wss:') {
        return;
    }
    
    // Cache static assets
    if (STATIC_FILES.some(file => url.pathname === file || url.pathname === '/')) {
        event.respondWith(
            caches.match(event.request).then((response) => {
                return response || fetch(event.request).then((response) => {
                    // Cache the response
                    const responseClone = response.clone();
                    caches.open(STATIC_CACHE).then((cache) => {
                        cache.put(event.request, responseClone);
                    });
                    return response;
                });
            })
        );
    } else {
        // Network first for other requests
        event.respondWith(
            fetch(event.request).catch(() => {
                return caches.match(event.request);
            })
        );
    }
});

// Background sync for offline message queue (future enhancement)
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-messages') {
        event.waitUntil(syncMessages());
    }
});

async function syncMessages() {
    // TODO: Implement offline message queue sync
    console.log('Syncing offline messages...');
}
