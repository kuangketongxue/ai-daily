"""
AI 热点日报 — AI 处理模块
用 DeepSeek 筛选+总结，只保留对目标用户有价值的内容
"""
import json
import os
import requests
from datetime import datetime

API_URL = 'https://api.chatst.org/v1/chat/completions'
API_KEY = 'sk-AUFCHc3jdS0lCjWQySpwKP7l15AehGYQ1wZr2KbNEBIrDfna'
MODEL = 'deepseek-v4-flash'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw')
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed')

SYSTEM_PROMPT = """你是一个AI新闻编辑，专门为一名"正在复读高考、同时想用AI赚钱的中国大学生"筛选和总结AI新闻。

## 筛选标准
保留以下类型的新闻：
1. **能直接用的AI工具/产品**（能帮我提效、赚钱、学习的）
2. **重大行业动态**（影响AI行业格局的，如大公司发布新模型、开源项目）
3. **赚钱机会**（AI相关的新平台、新玩法、变现路径）
4. **学习资源**（免费教程、开源项目、学习路径）
5. **高考相关AI应用**（AI学习工具、AI辅助备考）

过滤掉以下内容：
- 纯学术论文（除非有直接应用价值）
- 企业内部管理新闻
- 纯融资/估值新闻（除非有行业影响）
- 重复/相似的新闻只保留最重要的一条

## 输出格式
返回JSON数组，每个元素包含：
- "title": 简洁中文标题（15字以内）
- "summary": 一句话总结（50字以内，说清楚对"我"有什么用）
- "category": 分类（"工具" / "行业" / "赚钱" / "学习" / "其他"）
- "relevance": 相关度（1-5，5=必须看，1=可选）
- "url": 原文链接

只返回JSON数组，不要其他文字。最多保留25条。"""


def load_raw(date_str=None):
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
    path = os.path.join(RAW_DIR, f'{date_str}.json')
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_items_for_ai(items):
    """将原始条目格式化为AI可处理的文本"""
    lines = []
    for i, item in enumerate(items[:50]):  # 限制50条避免token超限
        title = item.get('title', '')
        summary = (item.get('summary') or '')[:150]
        source = item.get('source_name', item.get('source', ''))
        url = item.get('url', '')
        cat = item.get('category', '')
        lines.append(f'[{i+1}] {title}\n    来源: {source} | 分类: {cat}\n    摘要: {summary}\n    链接: {url}')
    return '\n\n'.join(lines)


def call_ai(items_text):
    """调用AI API进行筛选和总结"""
    user_prompt = f"以下是今天采集到的AI新闻（共{len(items_text.split(chr(10)))}条左右），请按筛选标准处理：\n\n{items_text}"

    try:
        r = requests.post(
            API_URL,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {API_KEY}',
            },
            json={
                'model': MODEL,
                'messages': [
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': user_prompt},
                ],
                'max_tokens': 4000,
                'temperature': 0.3,
            },
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        content = data['choices'][0]['message']['content']

        # 提取JSON（可能被```json包裹）
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]

        content = content.strip()

        # 尝试解析，失败时修复常见问题
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 尝试修复截断的JSON
            # 找最后一个完整的 }
            last_brace = content.rfind('}')
            if last_brace > 0:
                # 确保数组闭合
                truncated = content[:last_brace + 1]
                if not truncated.startswith('['):
                    truncated = '[' + truncated
                if not truncated.endswith(']'):
                    truncated = truncated + ']'
                try:
                    return json.loads(truncated)
                except json.JSONDecodeError:
                    pass
            print(f'  [ERR] JSON解析失败，前200字符: {content[:200]}')
            return None
    except Exception as e:
        print(f'  [ERR] AI API 调用失败: {e}')
        return None


def process(date_str=None):
    """主流程：读取原始数据 → AI处理 → 保存"""
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')

    print(f'=== AI 处理 {date_str} ===')

    # 1. 加载原始数据
    items = load_raw(date_str)
    if not items:
        print('[ERR] 无原始数据')
        return None
    print(f'  原始数据: {len(items)} 条')

    # 2. 格式化为AI输入
    items_text = format_items_for_ai(items)

    # 3. 调用AI处理
    print('  正在调用AI筛选...')
    processed = call_ai(items_text)
    if not processed:
        print('[ERR] AI处理失败，使用原始数据')
        return items

    print(f'  AI处理完成: {len(processed)} 条（筛选率 {len(processed)}/{len(items)}）')

    # 4. 保存处理结果
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    out_path = os.path.join(PROCESSED_DIR, f'{date_str}.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)
    print(f'  已保存: {out_path}')

    return processed


if __name__ == '__main__':
    result = process()
    if result:
        for item in result[:5]:
            print(f'  [{item.get("relevance","?")}] {item.get("title","")} — {item.get("summary","")}')
