const PREFIX = 'gaboma-pwa-';
const CACHE = PREFIX + '__REVISION__' + '-assets';
const PAGES = PREFIX + '__REVISION__' + '-pages';
const ASSETS = __ASSETS__;

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await Promise.all(ASSETS.map(url => cache.add(url).catch(() => {})));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', event => event.waitUntil((async () => {
  for (const key of await caches.keys()) {
    if (key.startsWith(PREFIX) && key !== CACHE && key !== PAGES) await caches.delete(key);
  }
  await self.clients.claim();
})()));

function isPublicPage(url) {
  const path = url.pathname;
  if (path.startsWith('/admin') || path.startsWith('/compte') || path.startsWith('/paiements') || path.startsWith('/soumettre') || path.startsWith('/mes-applications') || path.startsWith('/inscription')) return false;
  return path === '/' || path.startsWith('/repertoire') || path.startsWith('/applications/') || path.startsWith('/conditions-utilisation') || path.startsWith('/faq');
}

async function remember(cacheName, request, response) {
  if (!response || !response.ok || response.redirected) return;
  if ((await response.clone().arrayBuffer()).byteLength > 1500000) return;
  const cache = await caches.open(cacheName);
  await cache.put(request, response);
  const keys = await cache.keys();
  for (let i = 0; i < keys.length - 40; i++) await cache.delete(keys[i]);
}

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;

  if (url.pathname.startsWith('/static/hub/') || url.pathname.startsWith('/media/')) {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE);
      const cached = await cache.match(request);
      const network = fetch(request).then(response => {
        remember(CACHE, request, response.clone());
        return response;
      }).catch(() => cached);
      return cached || network;
    })());
    return;
  }

  if (request.mode !== 'navigate' || !isPublicPage(url)) return;
  event.respondWith((async () => {
    const cache = await caches.open(PAGES);
    const cached = await cache.match(request);
    const network = fetch(request).then(response => {
      remember(PAGES, request, response.clone());
      return response;
    });
    if (!cached) return network;
    const timed = new Promise(resolve => setTimeout(() => resolve(cached), 350));
    return Promise.race([network.catch(() => cached), timed]);
  })());
});
