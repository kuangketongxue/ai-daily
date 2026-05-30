# AI 热点日报

每天自动采集 6 个 AI 数据源，生成精美的中文日报页面。

## 数据源

| 源 | 内容 | API Key |
|---|---|---|
| [AI热榜](https://aihot.virxact.com) | 中文 AI 日报 | ❌ 不需要 |
| [GitHub Trending](https://github.com/trending) | 24h 热门 AI 仓库 | ❌ 不需要 |
| [HackerNews](https://news.ycombinator.com) | AI 相关热帖 | ❌ 不需要 |
| [Product Hunt](https://producthunt.com) | AI 新产品 | ❌ 不需要 |
| 机器之心/量子位 | 中文 AI 媒体 RSS | ❌ 不需要 |
| [arXiv CS.AI](https://arxiv.org) | 最新 AI 论文 | ❌ 不需要 |

## 本地使用

```bash
pip install -r scripts/requirements.txt
python scripts/collect.py      # 采集数据
python scripts/generate_report.py  # 生成日报
start assets/index.html        # 打开浏览器查看
```

或直接双击 `open-daily.bat`。

## 自动化

- **GitHub Actions**: 每 30 分钟自动采集+生成，部署到 GitHub Pages
- **本地定时**: Windows Task Scheduler 每天 6:00 打开浏览器

## 项目结构

```
ai-daily/
├── scripts/
│   ├── collect.py          # 数据采集（6个源）
│   ├── generate_report.py  # 生成日报 JSON
│   └── requirements.txt
├── data/
│   ├── raw/                # 每日原始数据
│   └── archive/            # 历史归档
├── assets/
│   ├── index.html          # 日报页面（暗色主题）
│   └── latest.json         # 最新日报数据
├── .github/workflows/
│   └── daily-report.yml    # GitHub Actions
└── open-daily.bat          # 一键打开浏览器
```

## 技术栈

- Python 3.11（requests + beautifulsoup4 + feedparser）
- 零依赖 vanilla HTML/CSS/JS 前端
- GitHub Actions CI/CD
- GitHub Pages 部署
