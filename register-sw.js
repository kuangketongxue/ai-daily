/* Service Worker 只在 https / localhost 下可用；file:// 直接跳过，不报错。 */
(function () {
  'use strict';
  if (!('serviceWorker' in navigator)) return;
  var secure = location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  if (!secure) return;
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('sw.js', { scope: './' }).catch(function () { /* 注册失败不影响阅读 */ });
  });
})();
