# AI 热点日报

AI 筛选 + 总结，只为"赚钱+高考复读"学生定制。每天早上 6 点浏览器自动打开。

## 数据流

```
collect.py → process.py(AI筛选) → generate_report.py → 浏览器自动打开
                                        ↓
                                  xhs/generate_cards.py → 小红书图片卡片
                                  xhs/generate_caption.py → 小红书文案
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

## 小红书日报

每天自动生成 3-9 张图片卡片 + 文案，半自动发布到小红书。

```bash
python xhs/generate_cards.py    # 生成图片卡片
python xhs/generate_caption.py  # 生成文案
python xhs/publish.py           # 半自动发布（需确认）
```

或直接双击 `run_xhs.bat` 一键生成。

### 卡片规格

- 尺寸：1080×1440（小红书 3:4 比例）
- 风格：科技暗黑（霓虹绿+金色）
- 内容：封面图 + 每条热点一张卡片（标题+摘要+分类+相关度评分）

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
├── xhs/                    # 小红书模块
│   ├── generate_cards.py   # 图片卡片生成（Pillow）
│   ├── generate_caption.py # 文案生成
│   └── publish.py          # 半自动发布
├── data/
│   ├── raw/                # 原始采集数据
│   ├── processed/          # AI 处理结果
│   └── archive/            # 历史归档
├── output/xhs/             # 小红书输出（图片+文案）
├── assets/
│   ├── template.html       # 页面模板
│   ├── index.html          # 生成的自包含页面
│   └── latest.json         # 最新日报数据
├── .github/workflows/
│   └── daily-report.yml    # GitHub Actions
├── open-daily.bat          # 一键打开浏览器
└── run_xhs.bat             # 一键生成小红书内容
```

## 技术栈

- Python 3.11（requests + beautifulsoup4 + feedparser + Pillow）
- DeepSeek API（AI 筛选总结）
- opencli（B站数据采集）
- Pillow（图片卡片生成，1080×1440 科技暗黑风格）
- social-auto-upload（可选，半自动发布到小红书）
- 零依赖 vanilla HTML/CSS/JS 前端
- GitHub Pages 部署
