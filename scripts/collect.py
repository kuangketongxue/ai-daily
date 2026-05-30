"""
AI 热点日报 — 数据采集模块
6 个免费数据源，无需 API Key
"""
import requests
import hashlib
import json
import os
import time
import re
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36'
TIMEOUT = 15
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw')


def _hash_id(source, title, url):
    return hashlib.sha1(f'{source}:{title}:{url}'.encode()).hexdigest()[:12]


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _safe_get(url, **kwargs):
    try:
        r = requests.get(url, headers={'User-Agent': UA}, timeout=TIMEOUT, **kwargs)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f'  [WARN] {url[:60]}... -> {e}')
        return None


# ── Source 1: aihot.virxact.com ──────────────────────────────

def fetch_aihot():
    """中文 AI 日报（模型/产品/行业/论文/技巧）"""
    items = []
    r = _safe_get('https://aihot.virxact.com/api/public/daily')
    if not r:
        return items
    try:
        data = r.json()
        for entry in data.get('items', data if isinstance(data, list) else []):
            title = entry.get('title', '')
            url = entry.get('url', '')
            if not title:
                continue
            items.append({
                'id': _hash_id('aihot', title, url),
                'title': title,
                'url': url,
                'source': 'aihot',
                'source_name': 'AI热榜',
                'category': entry.get('category', 'ai-general'),
                'published_at': entry.get('published_at', _now_iso()),
                'summary': entry.get('summary', ''),
            })
        print(f'  [OK] aihot: {len(items)} items')
    except Exception as e:
        print(f'  [ERR] aihot parse: {e}')
    return items


# ── Source 2: GitHub Trending ─────────────────────────────────

def fetch_github_trending():
    """GitHub 24h 热门 AI 仓库"""
    items = []
    r = _safe_get('https://github.com/trending?since=daily&spoken_language_code=en')
    if not r:
        return items
    try:
        soup = BeautifulSoup(r.text, 'html.parser')
        repos = soup.select('article.Box-row')[:25]
        for repo in repos:
            name_el = repo.select_one('h2 a')
            if not name_el:
                continue
            name = name_el.get_text(strip=True).replace('\n', '').replace(' ', '')
            url = 'https://github.com' + name_el['href']
            desc_el = repo.select_one('p')
            desc = desc_el.get_text(strip=True) if desc_el else ''
            stars_el = repo.select_one('span.d-inline-block.float-sm-right')
            stars = stars_el.get_text(strip=True) if stars_el else ''

            # 简单 AI 过滤
            ai_keywords = ['ai', 'llm', 'gpt', 'claude', 'agent', 'model', 'neural',
                           'transformer', 'diffusion', 'embedding', 'rag', 'inference',
                           'machine-learning', 'deep-learning', 'nlp', 'vision', 'openai',
                           'anthropic', 'gemini', 'copilot', 'langchain', 'autogen']
            text_lower = (name + ' ' + desc).lower()
            if not any(kw in text_lower for kw in ai_keywords):
                continue

            items.append({
                'id': _hash_id('github', name, url),
                'title': f'⭐ {name}',
                'url': url,
                'source': 'github',
                'source_name': 'GitHub Trending',
                'category': 'ai-tools',
                'published_at': _now_iso(),
                'summary': desc,
                'meta': {'stars': stars},
            })
        print(f'  [OK] github trending: {len(items)} items')
    except Exception as e:
        print(f'  [ERR] github trending: {e}')
    return items


# ── Source 3: HackerNews ──────────────────────────────────────

def fetch_hackernews():
    """HackerNews AI 相关热帖（并发请求，限 30 条）"""
    import concurrent.futures
    items = []
    r = _safe_get('https://hacker-news.firebaseio.com/v0/topstories.json')
    if not r:
        return items
    try:
        story_ids = r.json()[:30]
        ai_kw = ['ai', 'gpt', 'llm', 'openai', 'anthropic', 'claude', 'gemini',
                  'machine learning', 'deep learning', 'neural', 'transformer',
                  'diffusion', 'agent', 'rag', 'embedding', 'model', 'copilot']

        def fetch_story(sid):
            sr = _safe_get(f'https://hacker-news.firebaseio.com/v0/item/{sid}.json')
            if not sr:
                return None
            story = sr.json()
            title = story.get('title', '')
            if not any(kw in title.lower() for kw in ai_kw):
                return None
            url = story.get('url', f'https://news.ycombinator.com/item?id={sid}')
            return {
                'id': _hash_id('hn', title, url),
                'title': title,
                'url': url,
                'source': 'hackernews',
                'source_name': 'HackerNews',
                'category': 'ai-general',
                'published_at': datetime.fromtimestamp(
                    story.get('time', 0), tz=timezone.utc
                ).isoformat(),
                'summary': '',
                'meta': {'score': story.get('score', 0)},
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(fetch_story, story_ids))
        items = [r for r in results if r]
        print(f'  [OK] hackernews: {len(items)} items')
    except Exception as e:
        print(f'  [ERR] hackernews: {e}')
    return items


# ── Source 4: Product Hunt ────────────────────────────────────

def fetch_producthunt():
    """Product Hunt AI 新产品"""
    items = []
    r = _safe_get('https://www.producthunt.com/feed?category=ai')
    if not r:
        # fallback: try the HTML page
        r = _safe_get('https://www.producthunt.com/topics/artificial-intelligence')
        if not r:
            return items
        try:
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.select('a[href*="/posts/"]')[:15]
            for link in links:
                title = link.get_text(strip=True)
                url = 'https://www.producthunt.com' + link['href']
                if not title or len(title) < 5:
                    continue
                items.append({
                    'id': _hash_id('ph', title, url),
                    'title': title,
                    'url': url,
                    'source': 'producthunt',
                    'source_name': 'Product Hunt',
                    'category': 'ai-products',
                    'published_at': _now_iso(),
                    'summary': '',
                })
            print(f'  [OK] producthunt (html): {len(items)} items')
            return items
        except Exception:
            pass
    try:
        soup = BeautifulSoup(r.text, 'html.parser')
        for entry in soup.find_all('item')[:15]:
            title = entry.find('title').get_text(strip=True) if entry.find('title') else ''
            link = entry.find('link')
            url = link.get_text(strip=True) if link else ''
            if not title:
                continue
            items.append({
                'id': _hash_id('ph', title, url),
                'title': title,
                'url': url,
                'source': 'producthunt',
                'source_name': 'Product Hunt',
                'category': 'ai-products',
                'published_at': entry.find('pubdate').get_text(strip=True) if entry.find('pubdate') else _now_iso(),
                'summary': '',
            })
        print(f'  [OK] producthunt: {len(items)} items')
    except Exception as e:
        print(f'  [ERR] producthunt: {e}')
    return items


# ── Source 5: 机器之心 / 量子位 RSS ──────────────────────────

def fetch_chinese_ai_media():
    """中文 AI 媒体 RSS"""
    import feedparser
    items = []
    feeds = [
        ('https://www.jiqizhixin.com/rss', '机器之心'),
        ('https://www.qbitai.com/feed', '量子位'),
    ]
    for feed_url, name in feeds:
        try:
            d = feedparser.parse(feed_url)
            for entry in d.entries[:10]:
                title = entry.get('title', '')
                url = entry.get('link', '')
                if not title:
                    continue
                summary = entry.get('summary', '')
                if summary:
                    summary = BeautifulSoup(summary, 'html.parser').get_text()[:200]
                items.append({
                    'id': _hash_id(name, title, url),
                    'title': title,
                    'url': url,
                    'source': name,
                    'source_name': name,
                    'category': 'ai-industry',
                    'published_at': entry.get('published', _now_iso()),
                    'summary': summary,
                })
            print(f'  [OK] {name}: {len([i for i in items if i["source"] == name])} items')
        except Exception as e:
            print(f'  [ERR] {name}: {e}')
    return items


# ── Source 6: arXiv CS.AI ─────────────────────────────────────

def fetch_arxiv():
    """arXiv 最新 AI 论文"""
    import feedparser
    items = []
    try:
        url = 'http://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=15'
        d = feedparser.parse(url)
        for entry in d.entries[:15]:
            title = entry.get('title', '').replace('\n', ' ').strip()
            link = entry.get('link', '')
            summary = entry.get('summary', '')[:200]
            if not title:
                continue
            items.append({
                'id': _hash_id('arxiv', title, link),
                'title': f'📄 {title}',
                'url': link,
                'source': 'arxiv',
                'source_name': 'arXiv',
                'category': 'ai-paper',
                'published_at': entry.get('published', _now_iso()),
                'summary': summary,
            })
        print(f'  [OK] arxiv: {len(items)} items')
    except Exception as e:
        print(f'  [ERR] arxiv: {e}')
    return items


# ── Main ──────────────────────────────────────────────────────

ALL_FETCHERS = [
    fetch_aihot,
    fetch_github_trending,
    fetch_hackernews,
    fetch_producthunt,
    fetch_chinese_ai_media,
    fetch_arxiv,
]


def collect_all():
    """运行所有 fetcher，去重，返回合并结果"""
    all_items = []
    for fetcher in ALL_FETCHERS:
        try:
            items = fetcher()
            all_items.extend(items)
        except Exception as e:
            print(f'  [FATAL] {fetcher.__name__}: {e}')
        time.sleep(0.5)

    # 去重（按 title 前 20 字符 + url）
    seen = set()
    deduped = []
    for item in all_items:
        key = f'{item["title"][:20]}:{item["url"]}'
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    # 按时间排序（最新的在前）
    deduped.sort(key=lambda x: x.get('published_at', ''), reverse=True)

    print(f'\n=== 总计: {len(deduped)} items (去重前 {len(all_items)}) ===')
    return deduped


def save_raw(items):
    """保存原始采集数据"""
    os.makedirs(DATA_DIR, exist_ok=True)
    date_str = datetime.now().strftime('%Y-%m-%d')
    path = os.path.join(DATA_DIR, f'{date_str}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f'已保存: {path} ({len(items)} items)')
    return path


if __name__ == '__main__':
    print(f'=== AI 日报数据采集 {datetime.now().strftime("%Y-%m-%d %H:%M")} ===')
    items = collect_all()
    save_raw(items)
