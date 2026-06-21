# Amazon 进货选品推荐系统

基于 **Loop Engineering** 思想与 **Cursor Agent** 实践，根据用户输入的商品类别/关键词，在 Amazon.com 搜索并采集商品数据，按 BSR（销量代理指标）+ 评分综合排名，输出 Top N 进货推荐报告（含图片、评论数、评论正文、商品名等）。

---

## 功能概览

| 能力 | 说明 |
|------|------|
| 关键词/类别搜索 | 输入如 `wireless earbuds`，抓取 Amazon 搜索结果 |
| 详情 enrichment | 补充 BSR、主图、Bullet Points、Prime 标识 |
| 评论采集 | 每商品抓取最近 N 条评论（标题、正文、星级、日期） |
| 综合排名 | BSR + 评分 + 评论置信度加权排序 |
| 报告输出 | JSON + Markdown，含商品图片链接 |
| Web 界面 | FastAPI + 浏览器选品看板 |
| Loop 迭代 | Ralph / Fixed / Dynamic 三种 Loop 模式自愈与监控 |

---

## 网络调研结论

### 官方 API 现状

| 方案 | 可行性 | 说明 |
|------|--------|------|
| **Amazon PA-API 5.0** | 不推荐 | 2026-05-15 弃用，迁移至 Creators API；`CustomerReviews.Count/StarRating` 对多数开发者不可用 |
| **自研 Playwright 爬虫** | 可行（本项目采用） | 开源项目已验证，需处理反爬与 DOM 变更 |
| **第三方 API** | 备选降级 | Rainforest / Apify / ScrapingBee 可作为 fallback |

### 销量数据说明

Amazon **不公开真实销量**。业界统一使用 **BSR（Best Seller Rank，数值越小销量越高）** 作为销量代理指标，部分工具通过类目回归模型估算月销量。

### 参考开源项目

| 项目 | 技术栈 | 可借鉴点 |
|------|--------|----------|
| [amazon-omniscient](https://github.com/Umair706/amazon-omniscient) | FastAPI + Playwright + TimescaleDB | BSR 历史、类目回归销量估算 |
| [amazon-product-research-skill](https://github.com/shen169/amazon-product-research-skill) | Python Skill + Best Seller 分析 | Potential Score 公式、Cursor Skill 结构 |
| [amazon-scraper-python](https://github.com/maivyly52-gif/amazon-scraper-python) | requests/Playwright 双模式 | 模块化 pipeline、CLI 设计 |
| [ScrapingBee/amazon-scraper-api](https://github.com/ScrapingBee/amazon-scraper-api) | 托管 API | 字段清单与 sort_by 参数参考 |

---

## 系统架构

```
用户输入 (类别/关键词 + TopN)
        │
        ▼
  Cursor Agent / CLI
        │
        ├── SearchScraper (Playwright 搜索页)
        │         └── ASIN 列表 + 基础字段
        │
        ├── ProductScraper (详情页)
        │         └── BSR / 主图 / Bullet Points
        │
        ├── ReviewScraper (评论页)
        │         └── 评论正文 / 星级 / 日期
        │
        ├── Ranker (BSR + Rating 综合分)
        │
        └── Exporter → output/*.json + output/*.md
                │
                └── Loop 定时复扫 (可选)
```

---

## 快速开始

### 1. 环境准备

```bash
cd amazon-sourcing
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

### 2. 配置

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

编辑 `.env`，可选配置代理：

```
PROXY_URL=http://user:pass@host:port
HEADLESS=true
REQUEST_DELAY_MIN=2.0
REQUEST_DELAY_MAX=5.0
```

### 3. 运行选品

```bash
python -m src.cli "wireless earbuds" --top 10 --max-reviews 10 --pages 2
```

输出文件位于 `output/` 目录：

- `{keyword}_{timestamp}.json` — 结构化数据
- `{keyword}_{timestamp}.md` — 可读进货报告

### 4. Web 界面（FastAPI）

启动 Web 服务：

```bash
python -m src.web
```

浏览器访问：**http://localhost:8000**

也可使用 uvicorn 直接启动：

```bash
uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000
```

Web 界面功能：
- 输入关键词、Top N、评论数、搜索页数
- 后台异步采集，实时显示进度
- 卡片展示商品图片、评分、BSR、评论
- 查看 `output/` 历史报告

API 端点：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | Web 界面 |
| POST | `/api/search` | 启动选品任务 |
| GET | `/api/jobs/{job_id}` | 查询任务状态 |
| GET | `/api/reports` | 历史报告列表 |
| GET | `/api/reports/{filename}` | 读取报告 JSON |

### 5. 运行测试

```bash
pytest tests/ -v
```

---

## 排名算法

配置见 [`config/ranking.yaml`](config/ranking.yaml)：

```
sales_score       = 1 / log10(bsr + 10)           # BSR 越小分越高
rating_score      = star_rating / 5.0
review_confidence = min(review_count / 1000, 1)

composite = 0.5 * sales_score + 0.3 * rating_score + 0.2 * review_confidence
```

当 BSR 缺失时，降级使用 `review_count * star_rating` 作为销量代理。

---

## 输出字段

| 字段 | 说明 |
|------|------|
| `asin` | Amazon 标准商品 ID |
| `title` | 商品名称 |
| `image_url` | 主图 URL |
| `price` | 当前价格 (USD) |
| `star_rating` | 平均星级 (1-5) |
| `review_count` | 评论总数 |
| `bsr` | Best Seller Rank |
| `bsr_category` | BSR 所属类目 |
| `composite_score` | 综合排名分 |
| `reviews[]` | 评论列表（star/title/body/date/verified） |
| `product_url` | 商品链接 |

---

## Loop Engineering 使用指南

本项目集成三层 Loop 机制，详见 [`PROMPT.md`](PROMPT.md)。

### Ralph Loop — 迭代修复

当 Amazon DOM 变更导致选择器失效时：

```
/ralph-loop "修复 search scraper 选择器，确保 pytest 通过" --max-iterations 10 --completion-promise "ALL_TESTS_PASS"
```

状态文件：
- [`.ralph/progress.md`](.ralph/progress.md) — 迭代进度
- [`.ralph/guardrails.md`](.ralph/guardrails.md) — 失败经验沉淀

### Fixed Loop — 定时复扫

监控品类 BSR 变化，发现新进爆款：

```
/loop 1d 复扫 wireless earbuds Top20，对比 output/ 历史 JSON 中 BSR 变化
```

### Dynamic Loop — Captcha 自愈

Agent 检测到 Captcha 后等待 30 分钟再重试，并更新 guardrails。

### Cursor Skill / Agent

- Skill: [`.cursor/skills/amazon-sourcing/SKILL.md`](.cursor/skills/amazon-sourcing/SKILL.md)
- Agent: [`.cursor/agents/amazon-sourcing.md`](.cursor/agents/amazon-sourcing.md)

自然语言触发示例：

```
帮我在 Amazon 搜索 yoga mat，取 Top 15，输出进货报告
```

---

## 项目结构

```
amazon-sourcing/
├── README.md                 # 本文档
├── PROMPT.md                 # Loop Engineering 完整提示词
├── config/
│   ├── ranking.yaml          # 排名权重
│   └── selectors.yaml        # CSS 选择器（DOM 变更时只改此处）
├── src/
│   ├── cli.py                # CLI 入口
│   ├── browser/              # Playwright 上下文 + 反爬
│   ├── scrapers/             # search / product / reviews
│   ├── pipeline/             # ranker + exporter
│   └── models/               # Pydantic 数据模型
├── output/                   # 运行结果
├── tests/
└── .cursor/                  # Cursor Skill + Agent
```

---

## 合规与风险提示

1. **用途限制**：本项目仅供内部进货研究与决策参考，不得用于大规模公开数据转售。
2. **请求频率**：默认请求间隔 2-5 秒，请勿提高频率以免触发封禁。
3. **Amazon ToS**：爬取行为可能违反 Amazon 服务条款，使用前请评估法律风险。
4. **反爬应对**：建议配置住宅代理；遇到 Captcha 时使用 Dynamic Loop 延迟重试。
5. **数据准确性**：BSR 为销量代理而非真实销量；价格/库存实时变化，报告仅供参考。

---

## 已知限制与后续优化

- [ ] BSR → 月销量估算（类目回归模型）
- [ ] 多站点支持（.co.uk / .de / .co.jp）
- [ ] 第三方 API fallback 开关
- [ ] 历史 BSR 趋势对比（需数据库）
- [x] Web UI 看板（FastAPI，见 `python -m src.web`）

---

## 许可证

MIT — 仅供学习与内部研究使用。
