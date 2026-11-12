/* ==========================================================================
   数据接入层 · 零依赖
   --------------------------------------------------------------------------
   现场读源站，不镜像全文、不落盘到公开仓库：
     RSS        → 最近 7 期的日期 / 180 字摘要 / 原文链接
     Markdown   → 任意一期的完整正文（7 期之外也能按日期打开，只是不列入往期页）
     dates.js   → 断网时的日期兜底（只含 7 个日期，不含正文）

   源站实测（2026-11-12）：上述地址均返回 Access-Control-Allow-Origin: *。
   ========================================================================== */
(function (root) {
  'use strict';

  var RSS_URL = 'https://daily.juya.uk/rss.xml';
  var MD_BASE = 'https://daily.juya.uk/markdown/';
  var ISSUE_BASE = 'https://daily.juya.uk/issues/';
  var RECENT_LIMIT = 7;
  var TTL = 5 * 60 * 1000;     // 与源站 Cache-Control: max-age=300 对齐
  var TIMEOUT = 9000;

  var cache = new Map();       // key → { at, value }
  var inflight = new Map();    // 同一请求合并，避免四个页面重复拉

  function getCached(key) {
    var hit = cache.get(key);
    if (hit && Date.now() - hit.at < TTL) return hit.value;
    return null;
  }

  function fetchText(url) {
    if (typeof fetch !== 'function') return Promise.reject(new Error('当前环境不支持网络请求'));
    var ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, TIMEOUT) : null;
    return fetch(url, {
      cache: 'no-cache',
      signal: ctrl ? ctrl.signal : undefined,
      credentials: 'omit',
      referrerPolicy: 'no-referrer'
    }).then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.text();
    }).finally(function () { if (timer) clearTimeout(timer); });
  }

  function once(key, producer) {
    var hit = getCached(key);
    if (hit) return Promise.resolve(hit);
    if (inflight.has(key)) return inflight.get(key);
    var p = producer().then(function (value) {
      cache.set(key, { at: Date.now(), value: value });
      inflight.delete(key);
      return value;
    }, function (err) {
      inflight.delete(key);
      throw err;
    });
    inflight.set(key, p);
    return p;
  }

  function validDate(d) {
    var s = String(d == null ? '' : d).trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
    var dt = new Date(s + 'T00:00:00Z');
    return !isNaN(dt.getTime()) && dt.toISOString().slice(0, 10) === s;
  }

  function beijingToday() {
    try { return new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Shanghai' }); }
    catch (e) { return new Date().toISOString().slice(0, 10); }
  }

  function fallbackDates() {
    var g = root && root.AI_DAILY_DATES;
    var arr = g && Array.isArray(g.dates) ? g.dates : [];
    return arr.filter(validDate).slice(0, RECENT_LIMIT);
  }

  function parseRss(xmlText) {
    var doc;
    if (typeof DOMParser === 'undefined') throw new Error('当前环境无法解析 RSS');
    doc = new DOMParser().parseFromString(xmlText, 'application/xml');
    if (doc.querySelector('parsererror')) throw new Error('RSS 格式异常');
    var items = [];
    var nodes = doc.querySelectorAll('channel > item');
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      function txt(tag) {
        var el = n.getElementsByTagName(tag)[0];
        return el ? (el.textContent || '').trim() : '';
      }
      var date = txt('title').trim();
      if (!validDate(date)) continue;
      items.push({
        date: date,
        link: txt('link') || ISSUE_BASE + date + '/',
        pubDate: txt('pubDate'),
        description: txt('description')
      });
    }
    return {
      title: (doc.querySelector('channel > title') || {}).textContent || '橘鸦AI早报',
      items: items
    };
  }

  function rss() {
    return once('rss', function () {
      return fetchText(RSS_URL + '?t=' + Math.floor(Date.now() / TTL)).then(parseRss);
    });
  }

  // 往期页只列最近 7 期；RSS 挂了就用本地日期兜底，摘要留空但页面仍可用
  function recent() {
    return rss().then(function (feed) {
      return feed.items.slice(0, RECENT_LIMIT).map(function (it) {
        return { date: it.date, description: it.description, link: it.link };
      });
    }).catch(function () {
      return fallbackDates().map(function (d) {
        return { date: d, description: '', link: ISSUE_BASE + d + '/' };
      });
    });
  }

  function summaries() {
    return recent().then(function (list) {
      var map = {};
      for (var i = 0; i < list.length; i++) map[list[i].date] = list[i];
      return map;
    });
  }

  function markdown(date) {
    if (!validDate(date)) return Promise.reject(new Error('日期不合法：' + date));
    return once('md:' + date, function () {
      return fetchText(MD_BASE + date + '.md');
    });
  }

  function issue(date) {
    if (!validDate(date)) return Promise.reject(new Error('日期不合法：' + date));
    return once('issue:' + date, function () {
      return markdown(date).then(function (text) {
        if (!text || text.length < 200) throw new Error('这一期内容为空');
        var parsed = root.IssueMD ? root.IssueMD.parse(text, date) : null;
        if (!parsed) throw new Error('解析器未加载');
        return parsed;
      });
    });
  }

  // 最近 7 期全文一次性建索引，用于「搜到具体某条新闻」。
  // 7 期体量小（约 200KB），限并发 3，失败的单期跳过，不影响其它期。
  function loadRecentIssues(dates, onProgress) {
    var list = (dates || []).filter(validDate).slice(0, RECENT_LIMIT);
    var out = [], cursor = 0, active = 0;
    return new Promise(function (resolve) {
      if (!list.length) { resolve(out); return; }
      function next() {
        if (cursor >= list.length && active === 0) {
          out.sort(function (a, b) { return b.date.localeCompare(a.date); });
          resolve(out);
          return;
        }
        while (active < 3 && cursor < list.length) {
          (function (d) {
            active++; cursor++;
            issue(d).then(function (iss) { out.push(iss); }, function () { /* 单期失败不拖垮全表 */ })
              .then(function () {
                active--;
                if (onProgress) { try { onProgress(out.length, list.length); } catch (e) {} }
                next();
              });
          })(list[cursor]);
        }
      }
      next();
    });
  }

  function originUrl(date) { return ISSUE_BASE + String(date) + '/'; }

  root.AIData = {
    RSS_URL: RSS_URL, MD_BASE: MD_BASE, ISSUE_BASE: ISSUE_BASE, RECENT_LIMIT: RECENT_LIMIT,
    validDate: validDate, beijingToday: beijingToday, fallbackDates: fallbackDates,
    parseRss: parseRss, rss: rss, recent: recent, summaries: summaries,
    markdown: markdown, issue: issue, loadRecentIssues: loadRecentIssues,
    originUrl: originUrl,
    _cache: cache
  };
})(typeof window !== 'undefined' ? window : globalThis);
