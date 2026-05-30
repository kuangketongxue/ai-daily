# AI 日报 — CLAUDE.md

## 项目概述
自动采集 AI 新闻 → AI 筛选总结 → 生成日报页面。面向"赚钱+高考复读"学生定制。

## 数据流
```
collect.py → data/raw/{date}.json
process.py → data/processed/{date}.json (AI筛选)
generate_report.py → assets/latest.json + assets/index.html (自包含)
```

## 数据源
| 源 | 方式 | 备注 |
|---|---|---|
| aihot.virxact.com | REST API | 覆盖 OpenAI/Anthropic/Google 等 |
| Hugging Face | RSS feed | 官方博客 |
| GitHub Trending | HTML 爬取 | AI 相关仓库过滤 |
| B站·橘鸦Juya | opencli + 公众号抓取 | 每日 AI 早报完整文字版 |

## AI 处理
- 模型：deepseek-v4-flash (via api.chatst.org)
- 筛选标准：赚钱机会 > 实用工具 > 学习资源 > 行业动态
- 输出：title / summary / category / relevance(1-5) / url

## 关键路径
| 文件 | 用途 |
|------|------|
| `scripts/collect.py` | 数据采集 |
| `scripts/process.py` | AI 筛选总结 |
| `scripts/generate_report.py` | 生成日报 |
| `assets/template.html` | 页面模板 |
| `assets/index.html` | 生成的自包含页面 |
| `data/raw/` | 原始采集数据 |
| `data/processed/` | AI 处理结果 |
| `data/archive/` | 历史归档 |

## 本地运行
```bash
pip install -r scripts/requirements.txt
python scripts/collect.py      # 采集
python scripts/process.py       # AI筛选
python scripts/generate_report.py  # 生成
start assets/index.html         # 打开
```

## 注意事项
- `/*__DATA__*/` 标记必须在同一行 `let DATA=null;` 后面
- B站 opencli 调用需要 60-120 秒超时
- AI API 偶尔返回 412/401，用上次处理结果兜底
- GitHub Trending 经常超时，不影响其他源
