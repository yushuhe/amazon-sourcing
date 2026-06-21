# Ralph Loop Progress

## Phase 1 — 文档与脚手架
- [x] README.md 创建完成
- [x] PROMPT.md 创建完成
- [x] 项目骨架 (requirements, config, src/) 搭建完成
- [x] Cursor Skill + Agent 创建完成

## Phase 2 — 爬虫核心
- [x] SearchScraper (search.py)
- [x] ProductScraper (product.py)
- [x] ReviewScraper (reviews.py)
- [x] anti_bot + browser context
- [x] selectors.yaml 外置

## Phase 3 — 排名与输出
- [x] Ranker (ranker.py)
- [x] Exporter (exporter.py)
- [x] CLI 入口 (cli.py)

## Phase 4 — Loop 集成
- [x] guardrails.md 初始化
- [x] test_ranker.py 单元测试（3 passed）
- [ ] 端到端 live 验证（需 `playwright install chromium` 或系统 Chrome + 可访问 Amazon）

## 端到端验证说明

在已安装 Playwright 且网络可用的环境中运行：

```bash
cd amazon-sourcing
pip install -r requirements.txt
playwright install chromium
python -m src.cli "bluetooth speaker" --top 5 --max-reviews 3 --pages 1
```

若遇 Captcha，配置 `.env` 中 `PROXY_URL` 后重试。
