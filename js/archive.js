/* ==========================================================================
   往期回顾 · 搜索 / 筛选 / 分组（纯函数）+ 页面装配
   --------------------------------------------------------------------------
   AI 日报只列最近 7 期（用户 14:36 定）；万星日报仍列全部期次，不归这里管。
   搜索两层：按期次（日期 / 摘要 / 板块名）+ 按具体新闻条目（标题 / 正文）。
   7 期体量小，全文索引一次就能建完，所以「搜到某条新闻」是真能用的。
   ========================================================================== */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.ArchiveLogic = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  var DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

  function terms(q) {
    return String(q || '').trim().toLowerCase().split(/\s+/).filter(Boolean);
  }

  function issueHaystack(it, issueData) {
    var parts = [it.date, it.description || '', it.link || ''];
    if (issueData) {
      parts.push(issueData.title);
      for (var i = 0; i < issueData.sections.length; i++) parts.push(issueData.sections[i].name);
    }
    return parts.join(' ').toLowerCase();
  }

  function filterIssues(issues, query, group, issueMap) {
    var ts = terms(query);
    return (issues || []).filter(function (it) {
      if (!it || !DATE_RE.test(it.date || '')) return false;   // 非法日期不能拼进 ?d=
      if (group) {
        var d = issueMap && issueMap[it.date];
        var names = d ? d.sections.map(function (s) { return s.name; }) : [];
        if (names.indexOf(group) < 0) return false;
      }
      if (!ts.length) return true;
      var hay = issueHaystack(it, issueMap && issueMap[it.date]);
      return ts.every(function (t) { return hay.indexOf(t) >= 0; });
    });
  }

  // 在全文索引里搜具体新闻；返回 [{date, num, title, section, snippet}]
  function searchItems(parsedIssues, query, limit) {
    var ts = terms(query);
    if (!ts.length) return [];
    var out = [], cap = limit || 40;
    for (var i = 0; i < (parsedIssues || []).length; i++) {
      var iss = parsedIssues[i];
      for (var s = 0; s < iss.sections.length; s++) {
        var sec = iss.sections[s];
        for (var n = 0; n < sec.items.length; n++) {
          var it = sec.items[n];
          var text = [it.title, it.lead, sec.name].concat(it.blocks.map(function (b) { return b.text || ''; }))
            .join(' ').toLowerCase();
          if (!ts.every(function (t) { return text.indexOf(t) >= 0; })) continue;
          var snippet = '';
          for (var b = 0; b < it.blocks.length; b++) {
            var raw = String(it.blocks[b].text || '').replace(/[*`\[\]()]/g, '');
            var low = raw.toLowerCase(), at = low.indexOf(ts[0]);
            if (at >= 0) { snippet = raw.slice(Math.max(0, at - 30), at + 90); break; }
          }
          out.push({ date: iss.date, num: it.num, title: it.title, section: sec.name, snippet: snippet });
          if (out.length >= cap) return out;
        }
      }
    }
    return out;
  }

  function collectGroups(parsedIssues) {
    var counts = new Map();
    for (var i = 0; i < (parsedIssues || []).length; i++) {
      var secs = parsedIssues[i].sections || [];
      for (var j = 0; j < secs.length; j++) {
        var name = secs[j].name;
        counts.set(name, (counts.get(name) || 0) + secs[j].items.length);
      }
    }
    return Array.from(counts.entries())
      .sort(function (a, b) { return b[1] - a[1] || a[0].localeCompare(b[0], 'zh-CN'); })
      .map(function (e) { return { label: e[0], count: e[1] }; });
  }

  function groupByMonth(issues) {
    var sorted = (issues || []).slice().sort(function (a, b) { return b.date.localeCompare(a.date); });
    var groups = [];
    for (var i = 0; i < sorted.length; i++) {
      var key = sorted[i].date.slice(0, 7), g = groups[groups.length - 1];
      if (!g || g.key !== key) {
        g = { key: key, label: key.slice(0, 4) + ' 年 ' + Number(key.slice(5, 7)) + ' 月', items: [] };
        groups.push(g);
      }
      g.items.push(sorted[i]);
    }
    return groups;
  }

  return {
    DATE_RE: DATE_RE, terms: terms, issueHaystack: issueHaystack,
    filterIssues: filterIssues, searchItems: searchItems,
    collectGroups: collectGroups, groupByMonth: groupByMonth
  };
});
