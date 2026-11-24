/* AI 热点：读同域 data/aihot.json（由 scripts/build-aihot.py 现场生成）。
   来源与摘要只作索引，点击跳原站。渲染在页脚之前，不依赖首页原有逻辑。 */
(function () {
  const css = document.createElement('style');
  css.textContent = `
  #aihot{margin:40px auto 8px;max-width:760px;padding:0 16px}
  #aihot h2{font-size:18px;margin:0 0 12px;display:flex;align-items:center;gap:8px}
  #aihot h2 span{font-size:11px;font-weight:400;opacity:.55;letter-spacing:.5px}
  #aihot ul{list-style:none;margin:0;padding:0}
  #aihot li{padding:12px 0;border-top:1px solid rgba(255,255,255,.08)}
  #aihot a{color:inherit;text-decoration:none;font-size:15px;line-height:1.5;display:block}
  #aihot a:hover{opacity:.72}
  #aihot p{margin:4px 0 0;font-size:12.5px;opacity:.55;line-height:1.6}
  `;
  document.head.appendChild(css);

  fetch('data/aihot.json?t=' + Date.now())
    .then(r => r.ok ? r.json() : null)
    .then(d => {
      if (!d || !d.items || !d.items.length) return;
      const box = document.createElement('section');
      box.id = 'aihot';
      box.innerHTML = '<h2>AI 热点 <span>AIHOT · 每日更新</span></h2><ul>' +
        d.items.map(i => `<li><a href="${i.link}" target="_blank" rel="noopener">${i.title}</a>` +
          (i.summary ? `<p>${i.summary}</p>` : '') + '</li>').join('') + '</ul>';
      const foot = document.querySelector('footer.foot') || document.body;
      foot.parentNode.insertBefore(box, foot);
    })
    .catch(() => {});
})();
