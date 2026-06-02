"""
AI日报 × 小红书 — 文案生成器
从 processed JSON 生成小红书文案
"""
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output', 'xhs')

HASHTAGS = "#AI日报 #AI工具 #AI赚钱 #人工智能 #科技资讯 #ChatGPT #AIGC"


def generate_caption(items, date_str):
    """生成小红书文案"""
    # 日期格式美化
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    weekdays = ['一', '二', '三', '四', '五', '六', '日']
    date_display = f"{dt.month}月{dt.day}日 周{weekdays[dt.weekday()]}"

    lines = []
    lines.append(f"🤖 AI日报 | {date_display}")
    lines.append("")
    lines.append(f"今日AI圈最值得关注的{len(items)}件事👇")
    lines.append("")

    # emoji序列
    emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']

    for i, item in enumerate(items[:7]):
        title = item.get('title', '')
        summary = item.get('summary', '')
        category = item.get('category', '')

        # 分类emoji
        cat_emoji = {'工具': '🔧', '行业': '📊', '赚钱': '💰', '学习': '📚'}.get(category, '📌')

        emoji = emojis[i] if i < len(emojis) else f"{i+1}."
        line = f"{emoji} {cat_emoji} {title}"
        if summary:
            line += f"\n    {summary}"
        lines.append(line)
        lines.append("")

    lines.append("💡 你最关注哪条？评论区聊聊")
    lines.append("")
    lines.append(HASHTAGS)

    return "\n".join(lines)


def generate(date_str=None):
    """主入口"""
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')

    print(f'=== 生成小红书文案 {date_str} ===')

    # 读取数据
    processed_path = os.path.join(PROCESSED_DIR, f'{date_str}.json')
    raw_path = os.path.join(os.path.join(BASE_DIR, 'data', 'raw'), f'{date_str}.json')

    if os.path.exists(processed_path):
        with open(processed_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
    elif os.path.exists(raw_path):
        with open(raw_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
    else:
        print(f"  [ERR] 未找到 {date_str} 的数据")
        return None

    if not items:
        print("  [ERR] 无数据")
        return None

    # 按 relevance 排序
    items_sorted = sorted(items, key=lambda x: x.get('relevance', 0), reverse=True)
    top_items = items_sorted[:7]

    # 生成文案
    caption = generate_caption(top_items, date_str)

    # 保存
    output_dir = os.path.join(OUTPUT_DIR, date_str)
    os.makedirs(output_dir, exist_ok=True)
    caption_path = os.path.join(output_dir, 'caption.txt')
    with open(caption_path, 'w', encoding='utf-8') as f:
        f.write(caption)

    print(f"  [OK] caption saved: {caption_path}")
    return caption_path


if __name__ == '__main__':
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else None
    generate(date)
