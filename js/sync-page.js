/* ==========================================================================
   同步设置页逻辑
   --------------------------------------------------------------------------
   令牌只在这一个页面的密码框里出现，只写进浏览器 localStorage。
   本文件不含任何令牌、密钥；日志与错误信息一律脱敏。
   ========================================================================== */
(function (root) {
  'use strict';
  var CF = root.CloudFavorites;

  function $(id) { return document.getElementById(id); }
  function esc(s) { return root.IssueMD ? root.IssueMD.esc(s) : String(s == null ? '' : s); }

  function paintStatus(detail) {
    var el = $('sync-state');
    if (!el) return;
    var s = detail || CF.state();
    var text = {
      idle: '未连接', offline: '未连接（收藏只在这台设备）',
      syncing: '同步中', synced: '已同步到私有仓', error: '同步异常'
    }[s.phase] || s.phase;
    el.className = 'sync-state is-' + (s.phase === 'synced' ? 'ok' : (s.phase === 'error' ? 'bad' : (s.phase === 'syncing' ? 'busy' : 'idle')));
    el.innerHTML = '<strong>' + esc(text) + '</strong>'
      + '<span>' + esc(s.message || '') + '</span>'
      + '<span class="sync-meta">待上传改动 ' + Number(s.pending || 0) + ' 项'
      + (s.at ? ' · 最近一次 ' + esc(s.at.slice(0, 19).replace('T', ' ')) : '') + '</span>';
  }

  function paintToken() {
    var el = $('token-state');
    if (!el) return;
    var has = CF.hasToken();
    el.textContent = has ? '本机已保存令牌（只在这台设备的浏览器里，页面不会显示明文）' : '尚未设置令牌';
    el.className = 'token-state ' + (has ? 'is-on' : '');
    var clear = $('btn-clear-token');
    if (clear) clear.disabled = !has;
  }

  function init() {
    if (!CF) return;
    CF.configure({ site: 'ai-daily' });

    var link = $('token-setup-link');
    if (link) link.href = CF.tokenSetupUrl();

    var input = $('token-input');
    var msg = $('token-msg');

    $('btn-save-token') && $('btn-save-token').addEventListener('click', function () {
      var v = String(input.value || '').trim();
      msg.className = 'form-msg';
      if (!v) { msg.textContent = '请先粘贴令牌。'; msg.classList.add('is-err'); return; }
      // 只做形态检查，不打印、不回显、不记录令牌内容
      if (!/^github_pat_[A-Za-z0-9_]{20,}$/.test(v) && !/^gh[pousr]_[A-Za-z0-9]{20,}$/.test(v)) {
        msg.textContent = '这看起来不像 GitHub 令牌，请检查是否复制完整。';
        msg.classList.add('is-err');
        return;
      }
      CF.setToken(v);
      input.value = '';
      msg.textContent = '已保存到本机。正在连接私有仓…';
      paintToken();
      CF.pull().then(function () { return CF.sync(); })
        .then(function () { msg.textContent = '已连上私有仓，收藏会自动同步。'; })
        .catch(function (e) {
          msg.textContent = '连接失败：' + (e && e.message ? e.message : '未知原因');
          msg.classList.add('is-err');
        });
    });

    $('btn-clear-token') && $('btn-clear-token').addEventListener('click', function () {
      CF.clearToken();
      input.value = '';
      msg.className = 'form-msg';
      msg.textContent = '已清除本机令牌。收藏仍保留在这台设备上，云端文件不受影响。';
      paintToken();
      paintStatus();
    });

    $('btn-sync-now') && $('btn-sync-now').addEventListener('click', function () {
      if (!CF.hasToken()) { msg.textContent = '请先设置令牌。'; msg.className = 'form-msg is-err'; return; }
      CF.sync().then(function (s) {
        msg.textContent = s.phase === 'synced' ? '同步完成。' : (s.message || '同步结束');
        msg.className = 'form-msg' + (s.phase === 'error' ? ' is-err' : '');
      });
    });

    $('btn-pull-now') && $('btn-pull-now').addEventListener('click', function () {
      if (!CF.hasToken()) { msg.textContent = '请先设置令牌。'; msg.className = 'form-msg is-err'; return; }
      CF.pull().then(function () {
        msg.textContent = '已从私有仓取回收藏。';
        msg.className = 'form-msg';
        paintStatus();
      }).catch(function (e) {
        msg.textContent = '取回失败：' + (e && e.message ? e.message : '未知原因');
        msg.className = 'form-msg is-err';
      });
    });

    // 短码导出 / 导入（和收藏夹页同一套能力）
    var panel = $('sync-shortcode');
    if (panel && root.FavUI) {
      root.FavUI.initSyncPanel(panel, null, null);
    }

    document.addEventListener('cloud:state', function (e) { paintStatus(e.detail); });
    paintToken();
    paintStatus();

    if (CF.hasToken() && CF.state().pending > 0) CF.sync().catch(function () {});
  }

  root.SyncPage = { init: init };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(typeof window !== 'undefined' ? window : globalThis);
