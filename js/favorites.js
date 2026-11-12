/* ==========================================================================
   收藏界面组件 · 基于 shared/cloud-favorites.js
   --------------------------------------------------------------------------
   收藏粒度两层：整期（issues）与单条新闻（items）。
   本机点一下立即生效，云端同步在后台进行；断网时改动排队，联网后自动补传。
   ========================================================================== */
(function (root) {
  'use strict';
  var CF = root.CloudFavorites;
  var esc = root.IssueMD ? root.IssueMD.esc : function (s) { return String(s == null ? '' : s); };

  function ready() {
    if (!CF) { console.warn('cloud-favorites.js 未加载'); return false; }
    CF.configure({ site: 'ai-daily' });
    return true;
  }

  var toastTimer = null;
  function toast(msg) {
    var el = document.getElementById('fav-toast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'fav-toast'; el.className = 'fav-toast';
      el.setAttribute('role', 'status');
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.classList.add('is-on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.classList.remove('is-on'); }, 2600);
  }

  function starSvg(filled) {
    return '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false">'
      + '<path d="M12 2.6l2.9 5.9 6.5.95-4.7 4.58 1.11 6.47L12 17.45 6.19 20.5 7.3 14.03 2.6 9.45l6.5-.95z" '
      + 'fill="' + (filled ? 'currentColor' : 'none') + '" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>';
  }

  function paint(btn, on, label) {
    btn.dataset.fav = on ? '1' : '0';
    btn.classList.toggle('is-on', on);
    btn.innerHTML = starSvg(on) + '<span>' + esc(on ? '已收藏 · 点击取消' : label) + '</span>';
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
  }

  function mountButton(container, kind, id, label) {
    if (!container || !ready()) return null;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'fav-btn';
    container.appendChild(btn);
    var on = CF.has(kind, id);
    paint(btn, on, label || '收藏');
    btn.addEventListener('click', function () {
      var wasOn = btn.dataset.fav === '1';
      if (wasOn) CF.remove(kind, id); else CF.add(kind, id);
      var now = CF.has(kind, id);
      paint(btn, now, label || '收藏');
      toast(now ? '已收藏' : '已取消收藏');
    });
    return btn;
  }

  function mountIssueButton(container, date) { return mountButton(container, 'issues', date, '收藏这一期'); }
  function mountItemButton(container, itemId) { return mountButton(container, 'items', itemId, '收藏这条'); }

  // 页面上所有 data-fav-slot 一次性装好（文章页的新闻卡片）
  function mountAllItemButtons(scope) {
    var nodes = (scope || document).querySelectorAll('[data-fav-slot]');
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (el.dataset.mounted) continue;
      el.dataset.mounted = '1';
      mountItemButton(el, el.getAttribute('data-fav-slot'));
    }
  }

  /* 顶部云端状态条：所有页面共用，一眼看出收藏有没有真的上云 */
  function mountStatusBar(container) {
    if (!container || !ready()) return;
    container.className = 'cloud-bar';
    function render(detail) {
      var s = detail || CF.state();
      var cls = s.phase === 'synced' ? 'ok' : (s.phase === 'error' ? 'bad' : (s.phase === 'syncing' ? 'busy' : 'idle'));
      container.className = 'cloud-bar is-' + cls;
      container.innerHTML = '<span class="cloud-dot"></span>'
        + '<span class="cloud-msg">' + esc(s.message || '') + '</span>'
        + '<a class="cloud-link" href="sync.html">同步设置 →</a>';
    }
    document.addEventListener('cloud:state', function (e) { render(e.detail); });
    render();
    // 有令牌且有待上传改动时，进页面自动补传一次
    if (CF.hasToken() && CF.state().pending > 0) CF.sync().catch(function () {});
  }

  /* ---------------- 收藏夹页 ---------------- */

  function itemCard(id) {
    var parts = String(id).split('#');
    var date = parts[0], num = parts[1];
    return '<article class="fav-item" data-fav-item="' + esc(id) + '">'
      + '<div class="fav-head"><div class="fav-main">'
      + '<p class="fav-date">' + esc(date) + ' · 第 ' + esc(num) + ' 条</p>'
      + '<h3 class="fav-title fav-item-title" data-title="' + esc(id) + '">正在读取标题…</h3>'
      + '</div><div class="fav-actions">'
      + '<a class="fav-goto" href="article.html?d=' + encodeURIComponent(date) + '#item-' + esc(num) + '">看全文</a>'
      + '<button type="button" class="fav-drop" data-kind="items" data-id="' + esc(id) + '">取消收藏</button>'
      + '</div></div></article>';
  }

  function issueCard(date, summary) {
    return '<article class="fav-item" data-fav-issue="' + esc(date) + '">'
      + '<div class="fav-head"><div class="fav-main">'
      + '<p class="fav-date">' + esc(date) + ' · 整期</p>'
      + '<h3 class="fav-title">AI 早报 ' + esc(date) + '</h3>'
      + (summary ? '<p class="fav-one">' + esc(summary) + '</p>' : '')
      + '</div><div class="fav-actions">'
      + '<a class="fav-goto" href="article.html?d=' + encodeURIComponent(date) + '">看全文</a>'
      + '<button type="button" class="fav-drop" data-kind="issues" data-id="' + esc(date) + '">取消收藏</button>'
      + '</div></div></article>';
  }

  function initFavoritesPage(rootEl, countEl) {
    if (!rootEl || !ready()) return;
    var doc = CF.localDoc().sites['ai-daily'];
    var issues = doc.issues.slice(), items = doc.items.slice();
    if (countEl) countEl.textContent = '共 ' + (issues.length + items.length) + ' 项收藏';

    if (!issues.length && !items.length) {
      rootEl.innerHTML = '<div class="empty"><p class="big" aria-hidden="true">☆</p>'
        + '<p>收藏夹还是空的。</p>'
        + '<p class="empty-hint">在首页收藏整期，或在文章页收藏单条新闻，它们会出现在这里。</p>'
        + '<p class="empty-hint">收藏先存本机，填了令牌后会自动同步到你的私有仓；换电脑也能取回。</p></div>';
      return;
    }

    rootEl.innerHTML = '<div class="loading" role="status">正在读取收藏<span class="dots"></span></div>';

    var html = '';
    var summaries = {};
    var summariesDone = root.AIData
      ? root.AIData.summaries().then(function (m) { summaries = m; }).catch(function () {})
      : Promise.resolve();

    // 单条收藏的标题要从对应期全文里捞；7 期之外的旧日期也照样尝试，源站有就能读
    var dateSet = {};
    for (var i = 0; i < items.length; i++) dateSet[items[i].split('#')[0]] = 1;
    var dates = Object.keys(dateSet);

    summariesDone.then(function () {
      var pending = dates.length;
      if (!pending) return finish();
      dates.forEach(function (d) {
        root.AIData.issue(d).then(function (iss) {
          for (var s = 0; s < iss.sections.length; s++) {
            for (var t = 0; t < iss.sections[s].items.length; t++) {
              var it = iss.sections[s].items[t];
              var slot = rootEl.querySelector('[data-title="' + it.id + '"]');
              if (slot) slot.textContent = it.title;
            }
          }
        }, function () {}).then(function () { if (--pending === 0) finish(); });
      });
      function finish() {}
    });

    html += '<div class="fav-list">';
    for (var a = 0; a < issues.length; a++) {
      html += issueCard(issues[a], summaries[issues[a]] ? summaries[issues[a]].description : '');
    }
    for (var b = 0; b < items.length; b++) html += itemCard(items[b]);
    html += '</div>';
    rootEl.innerHTML = html;

    var drops = rootEl.querySelectorAll('.fav-drop');
    for (var k = 0; k < drops.length; k++) {
      drops[k].addEventListener('click', function () {
        var kind = this.getAttribute('data-kind'), id = this.getAttribute('data-id');
        CF.remove(kind, id);
        toast('已取消收藏');
        initFavoritesPage(rootEl, countEl);
      });
    }
  }

  /* 导出 / 导入短码（纯本地字符串变换，不发网络请求） */
  function initSyncPanel(panel, rootEl, countEl) {
    if (!panel || !ready()) return;
    var body = panel.querySelector('.fav-sync-body');
    var mode = null;

    function render() {
      if (!mode) { body.hidden = true; body.innerHTML = ''; return; }
      body.hidden = false;
      if (mode === 'export') {
        body.innerHTML = '<p class="fav-sync-title">复制这段短码，在另一台设备点「导入收藏」粘贴即可。短码里只有日期和编号。</p>'
          + '<textarea class="fav-sync-box" readonly rows="3">' + esc(CF.exportCode()) + '</textarea>'
          + '<p><button type="button" class="read-btn fav-sync-copy">复制短码</button></p>';
        body.querySelector('.fav-sync-copy').addEventListener('click', function () {
          var box = body.querySelector('.fav-sync-box');
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(box.value).then(function () { toast('已复制。'); }, function () { box.select(); toast('已选中，按 Ctrl+C。'); });
          } else { box.select(); toast('已选中，按 Ctrl+C。'); }
        });
      } else {
        body.innerHTML = '<p class="fav-sync-title">粘贴旧设备导出的短码。导入会合并，不会覆盖现有收藏。</p>'
          + '<textarea class="fav-sync-box" rows="3" placeholder="粘贴短码"></textarea>'
          + '<p><button type="button" class="read-btn fav-sync-do">导入</button>'
          + '<button type="button" class="fav-sync-cancel">取消</button></p>'
          + '<p class="fav-sync-err" role="alert"></p>';
        var box = body.querySelector('.fav-sync-box'), errEl = body.querySelector('.fav-sync-err');
        body.querySelector('.fav-sync-do').addEventListener('click', function () {
          errEl.textContent = '';
          try { CF.importCode(box.value); }
          catch (e) { errEl.textContent = e.message || '短码不对。'; return; }
          mode = null; render();
          initFavoritesPage(rootEl, countEl);
          toast('已导入收藏。');
        });
        body.querySelector('.fav-sync-cancel').addEventListener('click', function () { mode = null; render(); });
      }
    }

    var btns = panel.querySelectorAll('.fav-sync-btn');
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener('click', function () {
        var act = this.dataset.act;
        mode = mode === act ? null : act;
        render();
      });
    }
    render();
  }

  root.FavUI = {
    ready: ready, toast: toast,
    mountIssueButton: mountIssueButton, mountItemButton: mountItemButton,
    mountAllItemButtons: mountAllItemButtons, mountStatusBar: mountStatusBar,
    initFavoritesPage: initFavoritesPage, initSyncPanel: initSyncPanel
  };
})(typeof window !== 'undefined' ? window : globalThis);
