/* ==========================================================================
   Service Worker · 两套缓存分开管
   --------------------------------------------------------------------------
   SHELL：页面骨架，带版本号；部署时改 SHELL_VER 即整体换新。
   BODY ：源站全文与索引，不随版本升级清空 —— 离线时旧期次仍能读。
   策略：
     - 源站 markdown / RSS / archive 的 GET → 缓存优先（离线必读）
     - 本站 data/* → 网络优先 + 1.5 秒超时回落（保证新鲜又不卡首屏）
     - 页面骨架 → 先用缓存，后台更新
     - 任何带 Authorization 的请求（GitHub API）一律不缓存、不拦截
   ========================================================================== */
const SHELL_VER = 'v1';
const SHELL = 'ai-daily-shell-' + SHELL_VER;
const BODY = 'ai-daily-body-v1';
const SHELL_FILES = [
  './', './index.html', './article.html', './archive.html',
  './favorites.html', './sync.html', './404.html',
  './style.css', './favicon.svg', './manifest.webmanifest',
  './data/dates.js',
  './js/md.js', './js/core.js', './js/favorites.js',
  './js/archive.js', './js/cloud-favorites.js', './js/sync-page.js',
  './img/hero-ai.jpg'
];
const SOURCE_HOST = 'daily.juya.uk';

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(SHELL_FILES).catch(() => {})).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.map(k =>
      (k.startsWith('ai-daily-shell-') && k !== SHELL) ? caches.delete(k) : Promise.resolve(false)
    ))).then(() => self.clients.claim())
  );
});

function isSource(url) { return url.hostname === SOURCE_HOST; }
function isApi(url) { return url.hostname === 'api.github.com'; }

function networkFirst(req, timeoutMs) {
  return new Promise(resolve => {
    let done = false;
    const finish = v => { if (!done) { done = true; resolve(v); } };
    const timer = setTimeout(() => finish(caches.match(req)), timeoutMs);
    fetch(req).then(res => {
      clearTimeout(timer);
      if (res && res.ok && req.method === 'GET') {
        const copy = res.clone();
        caches.open(BODY).then(c => c.put(req, copy)).catch(() => {});
      }
      finish(res);
    }).catch(() => { clearTimeout(timer); finish(caches.match(req)); });
  }).then(res => res || Response.error());
}

function cacheFirst(req) {
  return caches.match(req).then(hit => hit || fetch(req).then(res => {
    if (res && res.ok && req.method === 'GET') {
      const copy = res.clone();
      caches.open(BODY).then(c => c.put(req, copy)).catch(() => {});
    }
    return res;
  }).catch(() => caches.match(req))).then(res => res || Response.error());
}

function staleWhileRevalidate(req) {
  return caches.match(req).then(hit => {
    const net = fetch(req).then(res => {
      if (res && res.ok) {
        const copy = res.clone();
        caches.open(SHELL).then(c => c.put(req, copy)).catch(() => {});
      }
      return res;
    }).catch(() => hit);
    return hit || net;
  });
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (isApi(url)) return;                       // 令牌请求绝不经过缓存
  if (url.origin !== self.location.origin && !isSource(url)) return;

  if (isSource(url)) { e.respondWith(cacheFirst(req)); return; }
  if (url.pathname.indexOf('/data/') >= 0) { e.respondWith(networkFirst(req, 1500)); return; }
  if (req.mode === 'navigate' || url.pathname.endsWith('.html') || url.pathname.endsWith('/')) {
    e.respondWith(staleWhileRevalidate(req)); return;
  }
  e.respondWith(staleWhileRevalidate(req));
});
