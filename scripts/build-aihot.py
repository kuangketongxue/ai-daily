#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拉 AIHOT 精选 RSS，生成 data/aihot.json（首屏「AI 热点」列表）。

去重两条：① 本次 feed 内部按规范化标题 + 链接去重；② 与 data/aihot-seen.json 里的
历史索引去重，已出现过的条目不再重复展示。seen 只保留最近 1500 条，避免文件无限增长。

来源只作为离线索引使用（标题 + 摘要 + 跳转链接），不转载全文。
"""
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

FEED = "https://aihot.news/feed.xml?aihot_actor=9d611906-d369-43b4-bf20-6932ea5d05c9"
ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
OUT_DIR = (WEB if WEB.is_dir() else ROOT) / "data"
KEEP = 20
SEEN_MAX = 1500


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ai-daily-aihot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        return r.read().decode("utf-8", "replace")


def norm(s):
    return re.sub(r"[\s\W_]+", "", (s or "").lower())


def main():
    xml = fetch(FEED)
    root = ET.fromstring(xml)
    ch = root.find("channel")
    if ch is None:
        print("FAIL: 缺少 channel", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    seen_path = OUT_DIR / "aihot-seen.json"
    seen = []
    if seen_path.exists():
        try:
            seen = json.loads(seen_path.read_text(encoding="utf-8"))
        except Exception:
            seen = []
    seen_set = set(seen)

    items, local, dup = [], set(), 0
    for it in ch.findall("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        desc = re.sub(r"<[^>]+>", " ", it.findtext("description") or "")
        desc = re.sub(r"\s+", " ", desc).strip()[:220]
        pub = (it.findtext("pubDate") or "").strip()
        if not title or not link:
            continue
        key = norm(title)
        if key in local or norm(link) in local:
            dup += 1
            continue
        if key in seen_set:          # 历史上出现过的，跳过
            dup += 1
            continue
        local.add(key)
        local.add(norm(link))
        items.append({"title": title, "link": link, "summary": desc, "pub": pub})
        if len(items) >= KEEP:
            break

    payload = {
        "generated": date.today().isoformat(),
        "source": "https://aihot.news/",
        "count": len(items),
        "items": items,
    }
    (OUT_DIR / "aihot.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 回读断言
    back = json.loads((OUT_DIR / "aihot.json").read_text(encoding="utf-8"))
    if back["count"] != len(items) or back["items"] != items:
        print("FAIL: 回读不一致", file=sys.stderr)
        return 4
    titles = [norm(i["title"]) for i in items]
    if len(titles) != len(set(titles)):
        print("FAIL: 标题去重失败", file=sys.stderr)
        return 4

    seen.extend(titles)
    seen_path.write_text(json.dumps(seen[-SEEN_MAX:], ensure_ascii=False), encoding="utf-8")
    print(f"OK  AIHOT {len(items)} 条（去重跳过 {dup} 条）-> data/aihot.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
