#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 web/data/dates.js（file:// 可读）与 dates.json。

默认：从 RSS 取最近 7 期，作为 AI 日报往期回顾与离线兜底。
可选 --all：改从 /archive/ 拉全量日期（能力保留，默认不用）。
只存日期索引，不存正文 —— 源站 robots.txt 允许建索引（search=yes）。

用户口径（2026-11-12）：AI 日报只要最近 7 期；万星日报要全部期次。
万星日报的往期不归本脚本管，仍由它自己的 data/index.json 负责。

校验（T04）：格式 / 去重 / 倒序 / 条数突降告警 / 回读逐字一致，失败即非零退出。
"""
import argparse
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 本地源码树是 web/ 子目录，仓库根直接就是站点内容；两种布局都要能跑
WEB = ROOT / "web"
OUT_DIR = (WEB if WEB.is_dir() else ROOT) / "data"
RSS_URL = "https://daily.juya.uk/rss.xml"
ARCHIVE_URL = "https://daily.juya.uk/archive/"
ARCHIVE_DATE_RE = re.compile(r"/issues/(\d{4}-\d{2}-\d{2})/")
STRICT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DEFAULT_LIMIT = 7


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "ai-daily-index-builder/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} for {url}")
        return resp.read().decode("utf-8", "replace")


def valid_date(s: str) -> bool:
    if not STRICT_RE.match(s):
        return False
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def from_rss(limit: int):
    root = ET.fromstring(fetch(RSS_URL))
    channel = root.find("channel")
    if channel is None:
        raise RuntimeError("RSS 缺少 channel 节点")
    found = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        if valid_date(title):
            found.append(title)
    return sorted(set(found), reverse=True)[:limit]


def from_rss_items(limit: int):
    """最近若干期的轻量条目：日期 + 摘要 + 原文链接。

    为什么要有它：首页过去必须先把源站 400KB+ 的 RSS 整个拉下来才能显示
    「今天有什么」，跨境网络下常见 6~9 秒白屏，超时还会静默回落到旧索引。
    这份同域小文件（约 3KB）让首屏不必等大 RSS。
    """
    root = ET.fromstring(fetch(RSS_URL))
    channel = root.find("channel")
    if channel is None:
        raise RuntimeError("RSS 缺少 channel 节点")
    seen, items = set(), []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        if not valid_date(title) or title in seen:
            continue
        seen.add(title)
        desc = (item.findtext("description") or "").strip()
        desc = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", desc))
        items.append({
            "date": title,
            "description": desc[:180],
            "link": (item.findtext("link") or "").strip() or f"https://daily.juya.uk/issues/{title}/",
        })
        if len(items) >= limit:
            break
    items.sort(key=lambda x: x["date"], reverse=True)
    return items


def from_archive():
    html = fetch(ARCHIVE_URL)
    found = ARCHIVE_DATE_RE.findall(html)
    if not found:
        raise RuntimeError("往期页没有解析到任何 /issues/<日期>/ 链接，源站可能改版")
    return sorted(set(found), reverse=True)


def _parse_rss(xml: str, limit: int):
    """一次解析同时得到「日期索引」与「轻量条目」，避免重复下载 400KB+ RSS。"""
    root = ET.fromstring(xml)
    channel = root.find("channel")
    if channel is None:
        raise RuntimeError("RSS 缺少 channel 节点")
    found, seen, items = [], set(), []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        if not valid_date(title):
            continue
        if title not in seen:
            seen.add(title)
            found.append(title)
        if len(items) < limit:
            desc = (item.findtext("description") or "").strip()
            desc = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", desc))
            items.append({
                "date": title,
                "description": desc[:180],
                "link": (item.findtext("link") or "").strip()
                or f"https://daily.juya.uk/issues/{title}/",
            })
    dates = sorted(set(found), reverse=True)[:limit]
    items.sort(key=lambda x: x["date"], reverse=True)
    return dates, items[:limit]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="拉全量日期（默认只取最近 7 期）")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="默认模式取几期")
    args = ap.parse_args()
    limit = max(1, args.limit)

    if args.all:
        dates = from_archive()
        _, items = _parse_rss(fetch(RSS_URL), limit)
    else:
        dates, items = _parse_rss(fetch(RSS_URL), limit)

    if not dates:
        print("FAIL: 没解析到任何合法日期", file=sys.stderr)
        return 2

    bad = [d for d in dates if not valid_date(d)]
    if bad:
        print(f"FAIL: 出现非法日期 {bad[:5]}", file=sys.stderr)
        return 2
    if len(dates) != len(set(dates)) or dates != sorted(dates, reverse=True):
        print("FAIL: 去重 / 倒序校验未通过", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    js_path = OUT_DIR / "dates.js"
    json_path = OUT_DIR / "dates.json"

    # 默认 7 期时，少于 5 期说明源站可能临时异常，拦住不写
    if json_path.exists() and not args.all:
        try:
            old = json.loads(json_path.read_text(encoding="utf-8"))
            old_dates = old.get("dates", []) if isinstance(old, dict) else []
            if old_dates and len(dates) < min(len(old_dates), 5):
                print(
                    f"FAIL: 新索引只剩 {len(dates)} 期（旧 {len(old_dates)} 期），疑似源站异常，"
                    "已停止写入（旧文件未动）",
                    file=sys.stderr,
                )
                return 3
        except (ValueError, OSError):
            pass

    payload = {
        "generated": date.today().isoformat(),
        "source": ARCHIVE_URL if args.all else RSS_URL,
        "mode": "all" if args.all else "recent",
        "count": len(dates),
        "dates": dates,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    js_path.write_text(
        "/* 由 scripts/build-dates.py 现场生成，勿手改。只含日期索引，不含正文。 */\n"
        "window.AI_DAILY_DATES = " + json.dumps(payload, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )

    back = json.loads(json_path.read_text(encoding="utf-8"))
    if back["dates"] != dates or back["count"] != len(dates):
        print("FAIL: 回读不一致", file=sys.stderr)
        return 4
    if "window.AI_DAILY_DATES" not in js_path.read_text(encoding="utf-8"):
        print("FAIL: JS 索引缺少全局变量", file=sys.stderr)
        return 4

    # 轻量首屏索引：首页先读它（同域 3KB），不再干等源站 400KB+ RSS
    if items:
        latest = {"generated": date.today().isoformat(), "source": RSS_URL, "count": len(items), "items": items}
        latest_path = OUT_DIR / "latest.json"
        latest_path.write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")
        back_latest = json.loads(latest_path.read_text(encoding="utf-8"))
        if back_latest.get("items") != items:
            print("FAIL: latest.json 回读不一致", file=sys.stderr)
            return 4

    print(f"OK  {payload['mode']}  {len(dates)} 期  {dates[-1]} ~ {dates[0]}  -> dates.js, dates.json"
          + (", latest.json" if items else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
