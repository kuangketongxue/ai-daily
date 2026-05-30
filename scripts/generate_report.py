"""
AI 热点日报 — 报告生成模块
读取采集数据，生成 JSON + 自包含 HTML 日报
"""
import json
import os
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw')
ARCHIVE_DIR = os.path.join(BASE_DIR, 'data', 'archive')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
TEMPLATE_PATH = os.path.join(ASSETS_DIR, 'template.html')

CATEGORY_LABELS = {
    'ai-models': '🧠 AI 模型',
    'ai-products': '🚀 AI 产品',
    'ai-tools': '🛠️ 开发工具',
    'ai-industry': '📰 行业动态',
    'ai-paper': '📄 论文',
    'ai-general': '🔥 综合热点',
    'tip': '💡 技巧',
}

CATEGORY_ORDER = [
    'ai-models', 'ai-products', 'ai-tools', 'ai-industry',
    'ai-paper', 'ai-general', 'tip',
]


def load_raw(date_str=None):
    """加载指定日期的原始数据"""
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
    path = os.path.join(RAW_DIR, f'{date_str}.json')
    if not os.path.exists(path):
        print(f'[WARN] 未找到 {path}')
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def categorize(items):
    """按分类分组"""
    groups = {}
    for item in items:
        cat = item.get('category', 'ai-general')
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(item)
    return groups


def build_report(items):
    """构建报告数据"""
    groups = categorize(items)

    # 统计来源
    sources = {}
    for item in items:
        src = item.get('source_name', item.get('source', 'unknown'))
        sources[src] = sources.get(src, 0) + 1

    report = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'generated_at': datetime.now().isoformat(),
        'total': len(items),
        'sources': sources,
        'categories': {},
    }

    for cat in CATEGORY_ORDER:
        if cat in groups:
            report['categories'][cat] = {
                'label': CATEGORY_LABELS.get(cat, cat),
                'items': groups[cat],
            }

    # 未分类的
    for cat, cat_items in groups.items():
        if cat not in report['categories']:
            report['categories'][cat] = {
                'label': CATEGORY_LABELS.get(cat, cat),
                'items': cat_items,
            }

    return report


def save_json(report):
    """保存 JSON"""
    path = os.path.join(ASSETS_DIR, 'latest.json')
    os.makedirs(ASSETS_DIR, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'已保存 JSON: {path}')
    return path


def generate_html(report):
    """生成自包含 HTML（数据内嵌，支持 file:// 协议打开）"""
    os.makedirs(ASSETS_DIR, exist_ok=True)

    # 读取模板
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            template = f.read()
    else:
        # 如果没有模板，用 index.html 作为模板
        index_path = os.path.join(ASSETS_DIR, 'index.html')
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                template = f.read()
        else:
            print('[ERR] 未找到模板文件')
            return None

    # 将 JSON 数据嵌入 HTML（替换 /*__DATA__*/ 标记）
    json_data = json.dumps(report, ensure_ascii=False)
    # 防止 </script> 注入
    json_data = json_data.replace('</script>', '<\\/script>')
    html = template.replace(
        'let DATA=null;/*__DATA__*/',
        f'let DATA={json_data};'
    )
    # 验证替换成功
    if 'DATA=null' in html and json_data != 'null':
        print('[ERR] DATA 替换失败，模板标记不匹配')
        return None

    out_path = os.path.join(ASSETS_DIR, 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'已生成 HTML: {out_path}')
    return out_path


def archive_report(date_str=None):
    """归档原始数据"""
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
    src = os.path.join(RAW_DIR, f'{date_str}.json')
    if os.path.exists(src):
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        dst = os.path.join(ARCHIVE_DIR, f'{date_str}.json')
        shutil.copy2(src, dst)
        print(f'已归档: {dst}')


if __name__ == '__main__':
    print(f'=== 生成 AI 日报 {datetime.now().strftime("%Y-%m-%d %H:%M")} ===')
    items = load_raw()
    if not items:
        print('[ERR] 无数据，请先运行 collect.py')
        exit(1)
    report = build_report(items)
    save_json(report)
    generate_html(report)
    archive_report()
    print(f'报告生成完成: {report["total"]} 条新闻, {len(report["sources"])} 个来源')
