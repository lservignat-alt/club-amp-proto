// Service worker du prototype Club AMP : l'app s'ouvre même sans réseau une fois installée.
// Changer VERSION à chaque mise en ligne pour forcer la mise à jour du cache.
const VERSION = 'club-amp-20261002-0925';
const COEUR = ['./', './index_10.html', './manifest.webmanifest', './img/icon-180.png', './img/icon-192.png', './img/icon-512.png', './data/terminaux3d.js'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(COEUR)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSION).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // Pages et vols en direct : réseau d'abord (pour recevoir les mises à jour), cache si hors connexion
  if (req.mode === 'navigate' || url.pathname.endsWith('/data/vols.json')) {
    e.respondWith(fetch(req).then(r => { const c = r.clone(); caches.open(VERSION).then(k => k.put(req, c)); return r; })
      .catch(() => caches.match(req).then(r => r || caches.match('./index_10.html'))));
    return;
  }
  // Données, modèles 3D, three.js et polices : cache d'abord (le plan officiel en ligne n'est pas mis en cache)
  if (url.origin === location.origin || /(^|\.)(cdnjs\.cloudflare\.com|cdn\.jsdelivr\.net|fonts\.googleapis\.com|fonts\.gstatic\.com)$/.test(url.hostname)) {
    e.respondWith(caches.match(req).then(r => r || fetch(req).then(res => {
      if (res.ok || res.type === 'opaque') { const c = res.clone(); caches.open(VERSION).then(k => k.put(req, c)); }
      return res;
    })));
  }
});
