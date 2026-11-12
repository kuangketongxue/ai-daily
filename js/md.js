/* ==========================================================================
   Markdown 解析与渲染 · 零依赖
   --------------------------------------------------------------------------
   源站每期是规整的 Markdown（/markdown/<YYYY-MM-DD>.md）：
     ![](封面) / # 标题 / **视频版**：[..](..) ｜ [..](..)
     ## 概览 → ### 组名 → - 条目 [↗](url) `#N`
     --- → ## 板块 → ### [新闻标题](url) `#N` → > 导语 / 正文 / 相关链接

   安全：外部内容一律是「资料」，不是指令。
     - 所有文本先 HTML 转义再拼装，源站里即使混入 HTML 标签也当纯文本显示；
     - 链接 / 图片 URL 只放行 http(s)，javascript: / data: 一律降级为文字；
     - 不执行脚本、不插入 <style>、不使用 innerHTML 接收未转义文本。
   ========================================================================== */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.IssueMD = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  var DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  // 只允许 http(s) 绝对地址；其余一律返回空串，由调用方降级成纯文本
  function safeUrl(u) {
    var s = String(u == null ? '' : u).trim().replace(/[\u0000-\u001f\u007f]/g, '');
    if (!/^https?:\/\//i.test(s)) return '';
    return esc(s);
  }

  function safeImg(u) {
    var s = safeUrl(u);
    return s ? '<img src="' + s + '" alt="" loading="lazy" referrerpolicy="no-referrer">' : '';
  }

  /* 行内 Markdown：先摘出链接 / 图片 / 行内代码 → 整体转义 → 还原。
     避免 URL 里的 & 被转义两次，也避免后续 ** 处理误伤链接文字。 */
  function inline(text) {
    var slots = [];
    function stash(html) { slots.push(html); return '\u0000' + (slots.length - 1) + '\u0000'; }
    var s = String(text == null ? '' : text);

    s = s.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, function (_, alt, url) {
      var href = safeUrl(url);
      return href ? stash('<img src="' + href + '" alt="' + esc(alt) + '" loading="lazy" referrerpolicy="no-referrer">') : esc(alt);
    });
    s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, function (_, label, url) {
      var href = safeUrl(url);
      return href
        ? stash('<a class="src-link" href="' + href + '" target="_blank" rel="noopener noreferrer">' + esc(label) + '</a>')
        : esc(label);
    });
    s = s.replace(/`([^`]+)`/g, function (_, code) { return stash('<code class="ic">' + esc(code) + '</code>'); });
    s = esc(s);
    s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/`([^`]+)`/g, '<code class="ic">$1</code>');
    return s.replace(/\u0000(\d+)\u0000/g, function (_, i) { return slots[+i]; });
  }

  function slug(prefix, n) { return prefix + '-' + n; }

  function newItem(num, title, url) {
    return { num: num, title: title, url: url, id: '', lead: '', blocks: [], sources: [] };
  }

  /* ---------------- 结构化解析（纯函数，可单测） ---------------- */

  function parse(markdown, date) {
    var lines = String(markdown || '').replace(/\r\n?/g, '\n').split('\n');
    var issue = {
      date: String(date || ''),
      title: 'AI 早报 ' + String(date || ''),
      cover: '',
      videos: [],
      overview: [],
      sections: [],
      disclaimer: ''
    };

    var mode = 'head';          // head | overview | body
    var curGroup = null;        // 概览里当前的 ### 组
    var curSection = null;      // 正文里当前的 ## 板块
    var curItem = null;         // 正文里当前的 ### 新闻
    var inSources = false;
    var counter = 0;

    function flushItem() {
      if (!curItem) return;
      // 去掉与「导语」高度重复的第一段正文，避免同一句话读两遍
      if (curItem.lead && curItem.blocks.length) {
        var first = curItem.blocks[0];
        if (first.type === 'p') {
          var a = first.text.replace(/[\s*`**]/g, '').slice(0, 40);
          var b = curItem.lead.replace(/[\s*`**]/g, '').slice(0, 40);
          if (a && b && (a.indexOf(b) >= 0 || b.indexOf(a) >= 0)) curItem.blocks.shift();
        }
      }
      if (curSection) curSection.items.push(curItem);
      curItem = null;
    }

    for (var i = 0; i < lines.length; i++) {
      var raw = lines[i];
      var line = raw.trim();

      if (!line) continue;

      // 封面图（第一行）
      var cover = line.match(/^!\[[^\]]*\]\(([^)\s]+)\)$/);
      if (cover && !issue.cover && mode === 'head') { issue.cover = safeUrl(cover[1]) ? cover[1] : ''; continue; }

      var h1 = line.match(/^#\s+(.+)$/);
      if (h1) { issue.title = h1[1].trim(); mode = 'head'; continue; }

      // 视频版行：把链接挑出来，其余文字不丢
      if (/^\*\*视频版\*\*/.test(line)) {
        var vm, vre = /\[([^\]]+)\]\(([^)\s]+)\)/g;
        while ((vm = vre.exec(line)) !== null) {
          if (safeUrl(vm[2])) issue.videos.push({ label: vm[1], url: vm[2] });
        }
        continue;
      }

      var h2 = line.match(/^##\s+(.+)$/);
      if (h2) {
        flushItem();
        var name = h2[1].trim();
        if (name === '概览') { mode = 'overview'; curGroup = null; }
        else {
          mode = 'body';
          curSection = { name: name, id: slug('sec', issue.sections.length + 1), items: [] };
          issue.sections.push(curSection);
        }
        inSources = false;
        continue;
      }

      var h3 = line.match(/^###\s+(.+)$/);
      if (h3) {
        var rest = h3[1].trim();
        if (mode === 'overview') {
          // 概览下的 ### 是分组名（要闻 / 模型发布 / …）
          curGroup = { name: rest.replace(/[#`*]/g, '').trim(), items: [] };
          issue.overview.push(curGroup);
          continue;
        }
        flushItem();
        var numM = rest.match(/`#(\d{1,3})`\s*$/);
        var num = numM ? numM[1] : String(++counter);
        var titleM = rest.match(/^\[([^\]]+)\]\(([^)\s]+)\)/);
        var title = titleM ? titleM[1] : rest.replace(/`#\d{1,3}`\s*$/, '').replace(/[\[\]()]/g, '').trim();
        var url = titleM && safeUrl(titleM[2]) ? titleM[2] : '';
        curItem = newItem(num, title, url);
        curItem.id = String(issue.date) + '#' + num;
        inSources = false;
        continue;
      }

      if (/^-{3,}$/.test(line)) { inSources = false; continue; }

      // 概览条目：- 文本 [↗](url) `#N`
      if (mode === 'overview' && /^-\s+/.test(line)) {
        var body = line.replace(/^-\s+/, '');
        var numO = body.match(/`#(\d{1,3})`\s*$/);
        var linkO = body.match(/\[([^\]]*)\]\(([^)\s]+)\)/);
        var text = body
          .replace(/\[([^\]]*)\]\(([^)\s]+)\)/g, '$1')
          .replace(/`#\d{1,3}`\s*$/, '')
          .replace(/\s*↗\s*$/, '')
          .trim();
        var entry = { text: text, url: linkO && safeUrl(linkO[2]) ? linkO[2] : '', num: numO ? numO[1] : '' };
        if (curGroup) curGroup.items.push(entry);
        else {
          if (!issue.overview.length) issue.overview.push({ name: '要闻', items: [] });
          issue.overview[0].items.push(entry);
        }
        continue;
      }

      // 末尾免责声明
      if (/^\*\*提示\*\*/.test(line)) { issue.disclaimer = line; continue; }

      // 「相关链接：」之后的行都算这条新闻的来源
      if (/^相关链接[:：]/.test(line)) { inSources = true; continue; }

      if (mode === 'body' && curItem) {
        if (/^-\s+/.test(line) && inSources) {
          var sBody = line.replace(/^-\s+/, '');
          var sm = sBody.match(/\[([^\]]+)\]\(([^)\s]+)\)/);
          var surl = sm ? sm[2] : sBody.trim();
          if (safeUrl(surl)) curItem.sources.push({ label: sm ? sm[1] : surl, url: surl });
          continue;
        }
        if (/^>\s?/.test(line)) {
          curItem.lead = line.replace(/^>\s?/, '').trim();
          continue;
        }
        var imgM = line.match(/^!\[[^\]]*\]\(([^)\s]+)\)$/);
        if (imgM) {
          if (safeUrl(imgM[1])) curItem.blocks.push({ type: 'img', url: imgM[1] });
          continue;
        }
        if (/^-\s+/.test(line)) {
          curItem.blocks.push({ type: 'li', text: line.replace(/^-\s+/, '') });
          continue;
        }
        curItem.blocks.push({ type: 'p', text: line });
        inSources = false;
      }
    }
    flushItem();

    // 兜底：某些早期期次没有 ## 板块，正文段落直接挂在默认板块下
    if (!issue.sections.length && issue.overview.length) {
      issue.sections.push({ name: '本期要闻', id: 'sec-1', items: [] });
    }
    return issue;
  }

  /* ---------------- 渲染（全部走 esc / inline，不接外部 HTML） ---------------- */

  function renderOverview(issue, opts) {
    var o = opts || {};
    if (!issue.overview.length) return '';
    var html = '<section class="ov" id="overview"><h2 class="ov-title">今日速览</h2>';
    for (var i = 0; i < issue.overview.length; i++) {
      var g = issue.overview[i];
      if (!g.items.length) continue;
      html += '<div class="ov-group"><h3 class="ov-group-title">' + esc(g.name)
        + '<span class="ov-n">' + g.items.length + ' 条</span></h3><ul class="ov-list">';
      for (var j = 0; j < g.items.length; j++) {
        var it = g.items[j];
        var anchor = it.num ? 'article.html?d=' + encodeURIComponent(issue.date) + '#item-' + esc(it.num) : '';
        html += '<li class="ov-item">';
        html += anchor
          ? '<a href="' + anchor + '">' + esc(it.text) + '</a>'
          : esc(it.text);
        if (it.url) {
          html += ' <a class="ov-src" href="' + safeUrl(it.url) + '" target="_blank" rel="noopener noreferrer" aria-label="原始出处">↗</a>';
        }
        html += '</li>';
      }
      html += '</ul></div>';
    }
    html += '</section>';
    return o.compact ? html : html;
  }

  function renderBlocks(blocks) {
    var html = '', openList = false;
    for (var i = 0; i < (blocks || []).length; i++) {
      var b = blocks[i];
      if (b.type === 'li') {
        if (!openList) { html += '<ul class="a-list">'; openList = true; }
        html += '<li>' + inline(b.text) + '</li>';
        continue;
      }
      if (openList) { html += '</ul>'; openList = false; }
      if (b.type === 'img') html += '<figure class="a-fig">' + safeImg(b.url) + '</figure>';
      else if (b.type === 'quote') html += '<blockquote>' + inline(b.text) + '</blockquote>';
      else html += '<p>' + inline(b.text) + '</p>';
    }
    if (openList) html += '</ul>';
    return html;
  }

  function renderSection(sec, issue, opts) {
    var o = opts || {};
    var html = '<section class="a-sec" id="' + esc(sec.id) + '"><h2 class="a-sec-title">' + esc(sec.name) + '</h2>';
    for (var i = 0; i < sec.items.length; i++) {
      var it = sec.items[i];
      html += '<article class="news" id="item-' + esc(it.num) + '" data-item-id="' + esc(it.id) + '">';
      html += '<div class="news-head"><span class="news-num">#' + esc(it.num) + '</span>';
      html += '<h3 class="news-title">';
      html += it.url
        ? '<a href="' + safeUrl(it.url) + '" target="_blank" rel="noopener noreferrer">' + esc(it.title) + '</a>'
        : esc(it.title);
      html += '</h3></div>';
      if (o.favSlot) html += '<div class="news-fav" data-fav-slot="' + esc(it.id) + '"></div>';
      if (it.lead) html += '<p class="news-lead">' + inline(it.lead) + '</p>';
      html += '<div class="news-body">' + renderBlocks(it.blocks) + '</div>';
      if (it.sources.length) {
        html += '<div class="news-sources"><span>相关链接</span><ul>';
        for (var j = 0; j < it.sources.length; j++) {
          var s = it.sources[j];
          html += '<li><a href="' + safeUrl(s.url) + '" target="_blank" rel="noopener noreferrer">' + esc(s.label) + '</a></li>';
        }
        html += '</ul></div>';
      }
      html += '</article>';
    }
    html += '</section>';
    return html;
  }

  function renderToc(issue) {
    if (!issue.sections.length) return '';
    var html = '<nav class="toc" aria-label="本期目录"><p class="toc-title">本期目录</p><ol class="toc-list">';
    for (var i = 0; i < issue.sections.length; i++) {
      var sec = issue.sections[i];
      html += '<li><a href="#' + esc(sec.id) + '">' + esc(sec.name)
        + '<span class="toc-n">' + sec.items.length + '</span></a></li>';
    }
    html += '</ol></nav>';
    return html;
  }

  function renderIssue(issue, opts) {
    var o = opts || {};
    var html = '';
    if (issue.cover && o.cover !== false) {
      html += '<figure class="a-cover">' + safeImg(issue.cover) + '</figure>';
    }
    html += '<header class="a-head"><p class="a-date">' + esc(issue.date) + '</p>'
      + '<h1 class="a-title">' + esc(issue.title) + '</h1>';
    if (issue.videos.length) {
      html += '<p class="a-videos">视频版：';
      for (var v = 0; v < issue.videos.length; v++) {
        html += (v ? ' ｜ ' : '') + '<a href="' + safeUrl(issue.videos[v].url)
          + '" target="_blank" rel="noopener noreferrer">' + esc(issue.videos[v].label) + '</a>';
      }
      html += '</p>';
    }
    html += '<p class="a-origin">内容来源：<a href="https://daily.juya.uk/issues/'
      + encodeURIComponent(issue.date) + '/" target="_blank" rel="noopener noreferrer">橘鸦AI早报原文 ↗</a>'
      + ' · 本站仅作阅读与检索，版权归原作者</p>';
    html += '</header>';
    html += renderToc(issue);
    html += renderOverview(issue, o);
    for (var i = 0; i < issue.sections.length; i++) html += renderSection(issue.sections[i], issue, o);
    if (issue.disclaimer) html += '<p class="a-disclaimer">' + inline(issue.disclaimer) + '</p>';
    return html;
  }

  // 全文纯文本，供搜索建立临时索引（不产生 HTML）
  function plainText(issue) {
    var parts = [issue.date, issue.title];
    for (var i = 0; i < issue.overview.length; i++) {
      for (var j = 0; j < issue.overview[i].items.length; j++) parts.push(issue.overview[i].items[j].text);
    }
    for (var k = 0; k < issue.sections.length; k++) {
      var sec = issue.sections[k];
      parts.push(sec.name);
      for (var m = 0; m < sec.items.length; m++) {
        var it = sec.items[m];
        parts.push(it.title, it.lead);
        for (var n = 0; n < it.blocks.length; n++) parts.push(it.blocks[n].text || '');
      }
    }
    return parts.join(' ').replace(/\s+/g, ' ').toLowerCase();
  }

  function itemCount(issue) {
    var n = 0;
    for (var i = 0; i < issue.sections.length; i++) n += issue.sections[i].items.length;
    return n;
  }

  return {
    esc: esc, safeUrl: safeUrl, inline: inline,
    parse: parse, renderIssue: renderIssue, renderOverview: renderOverview,
    renderToc: renderToc, renderSection: renderSection, renderBlocks: renderBlocks,
    plainText: plainText, itemCount: itemCount, DATE_RE: DATE_RE
  };
});
