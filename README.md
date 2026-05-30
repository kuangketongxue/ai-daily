# AI 热点日报

AI 筛选 + 总结，只为"赚钱+高考复读"学生定制。每天早上 6 点浏览器自动打开。

## 数据流

```
collect.py → process.py(AI筛选) → generate_report.py → 浏览器自动打开
```

## 数据源

| 源 | 方式 | 内容 |
|---|---|---|
| [AI热榜](https://aihot.virxact.com) | REST API | 覆盖 OpenAI/Anthropic/Google 等官方源 |
| [Hugging Face](https://huggingface.co/blog) | RSS | 官方博客 |
| [GitHub Trending](https://github.com/trending) | HTML 爬取 | AI 相关热门仓库 |
| [B站·橘鸦Juya](https://space.bilibili.com/285286947) | opencli + 公众号 | 每日 AI 早报完整文字版 |

## AI 筛选

用 DeepSeek 模型自动筛选，保留对"赚钱+高考复读"有价值的内容：
- 💰 赚钱机会（AI 变现路径、新平台）
- 🛠️ 实用工具（能直接用的 AI 产品）
- 📚 学习资源（免费教程、开源项目）
- 📰 行业动态（影响行业格局的新闻）

每条新闻附带相关度评分（⭐1-5）。

## 本地使用

```bash
pip install -r scripts/requirements.txt
python scripts/collect.py       # 1. 采集
python scripts/process.py       # 2. AI筛选
python scripts/generate_report.py  # 3. 生成
start assets/index.html         # 4. 打开
```

或直接双击 `open-daily.bat`。

## 自动化

- **Windows Task Scheduler**: 每天 6:00 自动打开浏览器
- **GitHub Actions**: 每 30 分钟自动采集+生成，部署到 GitHub Pages

## 项目结构

```
ai-daily/
├── scripts/
│   ├── collect.py          # 数据采集（4个源）
│   ├── process.py          # AI 筛选总结
│   ├── generate_report.py  # 生成日报
│   └── requirements.txt
├── data/
│   ├── raw/                # 原始采集数据
│   ├── processed/          # AI 处理结果
│   └── archive/            # 历史归档
├── assets/
│   ├── template.html       # 页面模板
│   ├── index.html          # 生成的自包含页面
│   └── latest.json         # 最新日报数据
├── .github/workflows/
│   └── daily-report.yml    # GitHub Actions
└── open-daily.bat          # 一键打开浏览器
```

## 技术栈

- Python 3.11（requests + beautifulsoup4 + feedparser）
- DeepSeek API（AI 筛选总结）
- opencli（B站数据采集）
- 零依赖 vanilla HTML/CSS/JS 前端
- GitHub Pages 部署
