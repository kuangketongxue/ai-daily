"""
AI 热点日报 — 数据采集（用户指定源）
4 个源，全部免费，无需 API Key
"""
import requests
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import feedparser

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36'
TIMEOUT = 20
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


def _parse_feed(url, source_name, category, max_items=10):
    """通用 RSS 解析"""
    items = []
    try:
        d = feedparser.parse(url)
        for entry in d.entries[:max_items]:
            title = entry.get('title', '').strip()
            link = entry.get('link', '')
            if not title or not link:
                continue
            summary = entry.get('summary', '')
            if summary:
                summary = BeautifulSoup(summary, 'html.parser').get_text()[:200]
            items.append({
                'id': _hash_id(source_name, title, link),
                'title': title,
                'url': link,
                'source': source_name,
                'source_name': source_name,
                'category': category,
                'published_at': entry.get('published', _now_iso()),
                'summary': summary,
            })
        print(f'  [OK] {source_name}: {len(items)} items')
    except Exception as e:
        print(f'  [ERR] {source_name}: {e}')
    return items


# ── Source 1: Hugging Face ────────────────────────────────────

def fetch_huggingface():
    return _parse_feed('https://huggingface.co/blog/feed.xml', 'Hugging Face', 'ai-tools', 8)


# ── Source 2: GitHub AI ───────────────────────────────────────

def fetch_github_ai():
    items = []
    r = _safe_get('https://github.com/trending?since=daily&spoken_language_code=en')
    if not r:
        return items
    try:
        soup = BeautifulSoup(r.text, 'html.parser')
        repos = soup.select('article.Box-row')[:20]
        for repo in repos:
            name_el = repo.select_one('h2 a')
            if not name_el:
                continue
            name = name_el.get_text(strip=True).replace('\n', '').replace(' ', '')
            url = 'https://github.com' + name_el['href']
            desc_el = repo.select_one('p')
            desc = desc_el.get_text(strip=True) if desc_el else ''
            ai_kw = ['ai', 'llm', 'gpt', 'claude', 'agent', 'model', 'neural',
                      'transformer', 'diffusion', 'embedding', 'rag', 'inference',
                      'machine-learning', 'deep-learning', 'nlp', 'openai', 'anthropic',
                      'gemini', 'copilot', 'langchain', 'autogen', 'vision']
            text_lower = (name + ' ' + desc).lower()
            if not any(kw in text_lower for kw in ai_kw):
                continue
            items.append({
                'id': _hash_id('GitHub AI', name, url),
                'title': f'⭐ {name}',
                'url': url,
                'source': 'GitHub AI',
                'source_name': 'GitHub AI',
                'category': 'ai-tools',
                'published_at': _now_iso(),
                'summary': desc,
            })
        print(f'  [OK] GitHub AI: {len(items)} items')
    except Exception as e:
        print(f'  [ERR] GitHub AI: {e}')
    return items


# ── Source 9: aihot.virxact.com ───────────────────────────────

def fetch_aihot():
    """aihot 精选（覆盖 OpenAI/Anthropic/Google/HuggingFace 等）"""
    items = []
    # 拉日报
    r = _safe_get('https://aihot.virxact.com/api/public/daily')
    if r:
        try:
            data = r.json()
            cat_map = {
                '模型发布/更新': 'ai-models',
                '产品发布/更新': 'ai-products',
                '行业动态': 'ai-industry',
                '论文研究': 'ai-paper',
                '技巧与观点': 'tip',
            }
            for section in data.get('sections', []):
                label = section.get('label', '')
                cat = cat_map.get(label, 'ai-general')
                for entry in section.get('items', []):
                    title = entry.get('title', '')
                    url = entry.get('sourceUrl', '')
                    if not title:
                        continue
                    items.append({
                        'id': _hash_id('aihot-daily', title, url),
                        'title': title,
                        'url': url,
                        'source': 'aihot',
                        'source_name': entry.get('sourceName', 'AI热榜'),
                        'category': cat,
                        'published_at': data.get('generatedAt', _now_iso()),
                        'summary': entry.get('summary', ''),
                    })
        except Exception as e:
            print(f'  [ERR] aihot daily: {e}')
    # 拉精选（补充更多条目）
    r2 = _safe_get('https://aihot.virxact.com/api/public/items?mode=selected&take=50')
    if r2:
        try:
            data2 = r2.json()
            for entry in data2.get('items', []):
                title = entry.get('title', '')
                url = entry.get('url', '')
                if not title:
                    continue
                items.append({
                    'id': _hash_id('aihot-sel', title, url),
                    'title': title,
                    'url': url,
                    'source': 'aihot',
                    'source_name': entry.get('source', 'AI热榜'),
                    'category': entry.get('category', 'ai-general'),
                    'published_at': entry.get('publishedAt', _now_iso()),
                    'summary': entry.get('summary', ''),
                })
        except Exception as e:
            print(f'  [ERR] aihot items: {e}')
    print(f'  [OK] aihot: {len(items)} items')
    return items


# ── Source 10: Bilibili 用户视频 ──────────────────────────────

def fetch_bilibili():
    """用 opencli 抓取 B 站 AI 早报 + 微信公众号文字版"""
    items = []
    uid = '285286947'
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        # 1. 获取视频列表
        result = subprocess.run(
            f'npx opencli bilibili user-videos {uid} --format json',
            capture_output=True, text=True, timeout=120, encoding='utf-8',
            shell=True
        )
        if result.returncode != 0:
            print(f'  [WARN] bilibili user-videos failed')
            return items

        # 解析 JSON（跳过非 JSON 行）
        output = result.stdout.strip()
        json_start = output.find('[')
        if json_start < 0:
            print(f'  [WARN] bilibili: no JSON in output')
            return items
        videos = json.loads(output[json_start:])

        # 2. 找今天的 AI 早报
        target = None
        for v in videos:
            if 'AI 早报' in v.get('title', '') and today in v.get('date', ''):
                target = v
                break
        if not target:
            print(f'  [OK] bilibili: 0 items (no AI 早报 for {today})')
            return items

        video_url = target.get('url', '')
        bvid = video_url.split('/')[-1]

        # 3. 获取视频描述
        desc_result = subprocess.run(
            f'npx opencli bilibili video {bvid} --format json',
            capture_output=True, text=True, timeout=120, encoding='utf-8',
            shell=True
        )
        wechat_url = None
        if desc_result.returncode == 0:
            desc_out = desc_result.stdout
            match = re.search(r'https://mp\.weixin\.qq\.com/s/\S+', desc_out)
            if match:
                wechat_url = match.group(0).rstrip('"}\n')

        # 4. 抓公众号文字版
        full_content = ''
        if wechat_url:
            try:
                wr = _safe_get(wechat_url)
                if wr:
                    wsoup = BeautifulSoup(wr.text, 'html.parser')
                    content_div = wsoup.select_one('#js_content') or wsoup.select_one('.rich_media_content')
                    if content_div:
                        full_content = content_div.get_text(separator='\n', strip=True)[:3000]
            except Exception as e:
                print(f'  [WARN] wechat fetch: {e}')

        items.append({
            'id': _hash_id('bilibili-早报', target['title'], video_url),
            'title': f'🎬 {target["title"]}',
            'url': video_url,
            'source': 'bilibili',
            'source_name': 'B站·橘鸦Juya',
            'category': 'ai-general',
            'published_at': today,
            'summary': full_content or '点击查看视频',
            'meta': {'plays': target.get('plays', 0), 'wechat_url': wechat_url or ''},
        })
        print(f'  [OK] bilibili: 1 item (AI 早报 + {"公众号文字版" if full_content else "无文字版"})')
    except Exception as e:
        print(f'  [ERR] bilibili: {e}')
    return items


# ── Main ──────────────────────────────────────────────────────

ALL_FETCHERS = [
    fetch_aihot,        # 覆盖 OpenAI/Anthropic/Google 等官方源
    fetch_huggingface,  # Hugging Face 官方博客
    fetch_github_ai,    # GitHub AI 趋势
    fetch_bilibili,     # B站用户视频
]


def collect_all():
    all_items = []
    for fetcher in ALL_FETCHERS:
        try:
            items = fetcher()
            all_items.extend(items)
        except Exception as e:
            print(f'  [FATAL] {fetcher.__name__}: {e}')

    seen = set()
    deduped = []
    for item in all_items:
        key = f'{item["title"][:20]}:{item["url"]}'
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    deduped.sort(key=lambda x: x.get('published_at', ''), reverse=True)
    print(f'\n=== 总计: {len(deduped)} items (去重前 {len(all_items)}) ===')
    return deduped


def save_raw(items):
    os.makedirs(DATA_DIR, exist_ok=True)
    date_str = datetime.now().strftime('%Y-%m-%d')
    path = os.path.join(DATA_DIR, f'{date_str}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f'已保存: {path} ({len(items)} items)')
    return path


if __name__ == '__main__':
    print(f'=== AI 日报采集 {datetime.now().strftime("%Y-%m-%d %H:%M")} ===')
    items = collect_all()
    save_raw(items)
