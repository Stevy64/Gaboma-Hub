const PREFIX = 'gaboma-pwa-';
const CACHE = PREFIX + '__REVISION__' + '-assets';
const ASSETS = __ASSETS__;
self.addEventListener('install', event => {
  // Migration immédiate : aucune page ni donnée métier ne dépend de ce cache.
  event.waitUntil(self.skipWaiting());
});
self.addEventListener('activate', event => event.waitUntil((async () => {
  // Supprime aussi les anciennes bibliothèques, coques et images hors ligne.
  for (const key of await caches.keys()) {
    if (key.startsWith(PREFIX) && key !== CACHE) await caches.delete(key);
  }
  await self.clients.claim();
})()));
async function store(request, response) {
  if (!response.ok || response.redirected) return;
  if ((await response.clone().arrayBuffer()).byteLength > 1000000) return;
  const cache = await caches.open(CACHE);
  await cache.put(request, response);
  const keys = await cache.keys();
  for (let i=0; i<keys.length-80; i++) await cache.delete(keys[i]);
}
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  // Navigation, comptes, API, médias et paiements restent gérés par le réseau.
  if (request.method !== 'GET' || request.mode === 'navigate' || url.origin !== self.location.origin || !url.pathname.startsWith('/static/hub/')) return;
  const response = (async () => {
    const cached = await caches.open(CACHE).then(cache => cache.match(request)).catch(() => undefined);
    if (cached && /\.[a-f0-9]{12}\./.test(url.pathname)) return cached;
    // Revalidation en arrière-plan pour les ressources sans empreinte.
    const network = fetch(request);
    const save = network.then(r => store(request, r.clone())).catch(() => {});
    event.waitUntil(save);
    return cached || network;
  })();
  event.respondWith(response);
});
