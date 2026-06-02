"""
AI日报 × 小红书 — 图片卡片生成器
从 processed JSON 生成 1080×1440 科技暗黑风格卡片
"""
import json
import os
import textwrap
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# ─── 配置 ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output', 'xhs')

# 卡片尺寸（小红书 3:4）
CARD_W, CARD_H = 1080, 1440

# 颜色方案（科技暗黑）
BG_COLOR = (10, 10, 15)           # 近黑背景
BG_SECONDARY = (18, 18, 28)      # 稍浅背景块
NEON_GREEN = (0, 255, 136)        # 霓虹绿（主色）
GOLD = (255, 215, 0)             # 金色（高相关度）
CYAN = (0, 200, 255)             # 青色（辅色）
WHITE = (240, 240, 245)          # 近白文字
GRAY = (140, 140, 160)           # 灰色辅助文字
DIM = (60, 60, 80)               # 暗色分隔线

# 分类对应颜色
CATEGORY_COLORS = {
    '工具': (0, 200, 255),     # 青色
    '行业': (180, 120, 255),   # 紫色
    '赚钱': (255, 215, 0),     # 金色
    '学习': (0, 255, 136),     # 绿色
    '其他': (140, 140, 160),   # 灰色
}

# 字体路径（Windows 自带）
FONT_BOLD = 'C:/Windows/Fonts/msyhbd.ttc'
FONT_REGULAR = 'C:/Windows/Fonts/msyh.ttc'

# ─── 字体加载 ─────────────────────────────────────────────
def load_font(size, bold=False):
    """加载字体，fallback到系统默认"""
    try:
        path = FONT_BOLD if bold else FONT_REGULAR
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

# ─── 绘制工具 ─────────────────────────────────────────────
def draw_rounded_rect(draw, xy, radius, fill):
    """绘制圆角矩形"""
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    draw.pieslice([x0, y0, x0 + 2*radius, y0 + 2*radius], 180, 270, fill=fill)
    draw.pieslice([x1 - 2*radius, y0, x1, y0 + 2*radius], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - 2*radius, x0 + 2*radius, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - 2*radius, y1 - 2*radius, x1, y1], 0, 90, fill=fill)

def draw_glow_line(draw, y, color, width=3, glow=8):
    """绘制发光线条"""
    # 外层辉光（半透明模拟）
    for i in range(glow, 0, -1):
        alpha = int(40 * (1 - i / glow))
        glow_color = tuple(list(color[:3]) + [alpha]) if len(color) == 3 else color
        draw.line([(60, y), (CARD_W - 60, y)], fill=color, width=1)
    # 主线
    draw.line([(60, y), (CARD_W - 60, y)], fill=color, width=width)

def wrap_text(text, font, max_width, draw):
    """中文自动换行"""
    lines = []
    current_line = ""
    for char in text:
        test = current_line + char
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width:
            if current_line:
                lines.append(current_line)
            current_line = char
        else:
            current_line = test
    if current_line:
        lines.append(current_line)
    return lines

# ─── 封面图生成 ────────────────────────────────────────────
def generate_cover(items, date_str, output_dir):
    """生成日报封面图（总览页）"""
    img = Image.new('RGB', (CARD_W, CARD_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_title = load_font(56, bold=True)
    font_date = load_font(28)
    font_item = load_font(26)
    font_num = load_font(48, bold=True)
    font_tag = load_font(20)
    font_footer = load_font(22)

    y = 100

    # 顶部标题
    draw.text((CARD_W // 2, y), "AI 日报", font=font_title, fill=NEON_GREEN, anchor='mt')
    y += 80
    draw.text((CARD_W // 2, y), date_str, font=font_date, fill=GRAY, anchor='mt')
    y += 60

    # 发光线
    draw_glow_line(draw, y, NEON_GREEN)
    y += 40

    # 今日热点数量
    draw.text((CARD_W // 2, y), f"今日 {len(items)} 条热点", font=load_font(24), fill=CYAN, anchor='mt')
    y += 60

    # 列表每条
    max_title_width = CARD_W - 220
    for i, item in enumerate(items[:9]):  # 最多9条
        num = f"{i+1:02d}"
        title = item.get('title', '')
        category = item.get('category', '其他')
        relevance = item.get('relevance', 3)

        # 序号（大号金色）
        draw.text((80, y), num, font=font_num, fill=GOLD if relevance >= 4 else CYAN)

        # 标题文字（自动换行）
        title_lines = wrap_text(title, font_item, max_title_width, draw)
        for j, line in enumerate(title_lines[:2]):  # 最多2行
            draw.text((160, y + j * 36), line, font=font_item, fill=WHITE)

        # 分类小标签
        cat_color = CATEGORY_COLORS.get(category, GRAY)
        tag_text = category
        tag_bbox = draw.textbbox((0, 0), tag_text, font=font_tag)
        tag_w = tag_bbox[2] - tag_bbox[0] + 20
        tag_h = tag_bbox[3] - tag_bbox[1] + 12
        tag_x = 160
        tag_y = y + len(title_lines) * 36 + 8
        draw_rounded_rect(draw, (tag_x, tag_y, tag_x + tag_w, tag_y + tag_h), 4, cat_color)
        draw.text((tag_x + 10, tag_y + 4), tag_text, font=font_tag, fill=BG_COLOR)

        y += max(100, len(title_lines) * 36 + 50)

        # 分隔线
        if i < len(items) - 1 and i < 8:
            draw.line([(80, y - 15), (CARD_W - 80, y - 15)], fill=DIM, width=1)

    # 底部
    draw_glow_line(draw, CARD_H - 120, NEON_GREEN)
    draw.text((CARD_W // 2, CARD_H - 80), "关注我，每天获取AI圈最值得关注的事",
              font=font_footer, fill=GRAY, anchor='mt')
    draw.text((CARD_W // 2, CARD_H - 45), "#AI日报 #AI工具 #AI赚钱 #人工智能",
              font=load_font(18), fill=DIM, anchor='mt')

    # 保存
    cover_path = os.path.join(output_dir, 'card_00_cover.png')
    img.save(cover_path, quality=95)
    print(f"  [OK] cover: {cover_path}")
    return cover_path

# ─── 单条热点卡片生成 ──────────────────────────────────────
def generate_item_card(item, index, date_str, output_dir):
    """生成单条热点卡片"""
    img = Image.new('RGB', (CARD_W, CARD_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    title = item.get('title', '未知标题')
    summary = item.get('summary', '')
    category = item.get('category', '其他')
    relevance = item.get('relevance', 3)
    url = item.get('url', '')

    cat_color = CATEGORY_COLORS.get(category, GRAY)

    font_header = load_font(22)
    font_title = load_font(48, bold=True)
    font_summary = load_font(30)
    font_category = load_font(24, bold=True)
    font_relevance = load_font(24)
    font_url = load_font(20)
    font_footer = load_font(22)
    font_big_num = load_font(120, bold=True)

    # ── 背景装饰 ──
    # 大号半透明序号（背景水印效果）
    draw.text((CARD_W - 200, 80), f"{index:02d}", font=font_big_num, fill=(20, 20, 35))

    # ── 顶部栏 ──
    y = 80
    # 左上角品牌标识
    draw_rounded_rect(draw, (60, y, 200, y + 38), 6, NEON_GREEN)
    draw.text((72, y + 5), "AI 日报", font=load_font(22, bold=True), fill=BG_COLOR)

    # 右上角日期
    draw.text((CARD_W - 60, y + 8), date_str, font=font_header, fill=GRAY, anchor='rt')

    y += 70

    # ── 发光分隔线 ──
    draw_glow_line(draw, y, cat_color)
    y += 50

    # ── 序号 + 分类 ──
    draw.text((80, y), f"#{index:02d}", font=load_font(36, bold=True), fill=GOLD)
    draw.text((170, y + 6), f"/ {category}", font=load_font(28), fill=cat_color)
    y += 70

    # ── 标题 ──
    title_lines = wrap_text(title, font_title, CARD_W - 160, draw)
    for line in title_lines[:3]:  # 最多3行
        draw.text((80, y), line, font=font_title, fill=WHITE)
        y += 62
    y += 30

    # ── 摘要 ──
    summary_lines = wrap_text(summary, font_summary, CARD_W - 160, draw)
    for line in summary_lines[:4]:  # 最多4行
        draw.text((80, y), line, font=font_summary, fill=GRAY)
        y += 42
    y += 50

    # ── 相关度评分条 ──
    draw.text((80, y), "相关度", font=font_relevance, fill=GRAY)
    bar_x = 220
    bar_w = 300
    bar_h = 16
    bar_y = y + 5
    # 背景条
    draw_rounded_rect(draw, (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), 8, DIM)
    # 填充条
    fill_w = int(bar_w * relevance / 5)
    bar_color = GOLD if relevance >= 4 else NEON_GREEN if relevance >= 3 else CYAN
    if fill_w > 0:
        draw_rounded_rect(draw, (bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), 8, bar_color)

    # 星级文字
    stars = "★" * relevance + "☆" * (5 - relevance)
    draw.text((bar_x + bar_w + 20, y), stars, font=font_relevance, fill=GOLD)
    y += 60

    # ── 底部区域 ──
    # 底部发光线
    draw_glow_line(draw, CARD_H - 160, cat_color)

    # 来源
    if url:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace('www.', '') if url else ''
        draw.text((80, CARD_H - 130), f"  {domain}", font=font_url, fill=GRAY)

    # 底部标签
    draw.text((80, CARD_H - 90), "#AI日报 #AI工具 #AI赚钱 #人工智能 #科技资讯",
              font=load_font(20), fill=DIM)

    # 关注引导
    draw.text((CARD_W - 60, CARD_H - 130), "关注获取每日AI热点",
              font=font_footer, fill=NEON_GREEN, anchor='rt')

    # 保存
    card_path = os.path.join(output_dir, f'card_{index:02d}.png')
    img.save(card_path, quality=95)
    return card_path

# ─── 主流程 ────────────────────────────────────────────────
def generate(date_str=None):
    """主入口：生成小红书卡片"""
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')

    print(f'=== 生成小红书卡片 {date_str} ===')

    # 1. 读取数据
    processed_path = os.path.join(PROCESSED_DIR, f'{date_str}.json')
    raw_path = os.path.join(os.path.join(BASE_DIR, 'data', 'raw'), f'{date_str}.json')

    if os.path.exists(processed_path):
        with open(processed_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
        print(f"  读取AI筛选结果: {len(items)} 条")
    elif os.path.exists(raw_path):
        with open(raw_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
        print(f"  读取原始数据: {len(items)} 条")
    else:
        print(f"  [ERR] 未找到 {date_str} 的数据")
        return []

    if not items:
        print("  [ERR] 无数据可处理")
        return []

    # 2. 按 relevance 排序，取前7条
    items_sorted = sorted(items, key=lambda x: x.get('relevance', 0), reverse=True)
    top_items = items_sorted[:7]

    # 3. 创建输出目录
    output_dir = os.path.join(OUTPUT_DIR, date_str)
    os.makedirs(output_dir, exist_ok=True)

    # 4. 生成封面
    generated = []
    cover = generate_cover(top_items, date_str, output_dir)
    generated.append(cover)

    # 5. 生成每条卡片
    for i, item in enumerate(top_items):
        card = generate_item_card(item, i + 1, date_str, output_dir)
        generated.append(card)
        print(f"  [OK] card {i+1}/{len(top_items)}: {item.get('title', '')[:20]}")

    print(f"\n  [DONE] {len(generated)} cards -> {output_dir}")
    return generated


if __name__ == '__main__':
    import sys
    date = sys.argv[1] if len(sys.argv) > 1 else None
    generate(date)
