---
name: amazon-sourcing
description: >-
  Amazon 进货选品：根据商品类别/关键词在 Amazon.com 搜索，按 BSR+评分排名输出 Top N 报告（含图片、评论、商品名）。
  使用 Playwright 自研爬虫 + Loop Engineering 迭代修复。当用户提到 Amazon 选品、进货推荐、商品搜索时使用。
---

# Amazon Sourcing Skill

## 何时使用

- 用户需要根据商品类别在 Amazon 搜索推荐商品
- 用户需要按销量(BSR)/评分排名取 Top N
- 用户需要商品图片、评论数、评论内容、商品名等字段
- 用户提到 Amazon 选品、进货、sourcing、FBA 研究

## 快速执行

```bash
cd amazon-sourcing
python -m src.cli "{keyword}" --top {top_n} --max-reviews {max_reviews} --pages {pages}
```

## 工作流

1. 确认输入：`keyword`、`top_n`（默认 20）、`max_reviews`（默认 10）
2. 运行 CLI（见上）
3. 读取 `output/` 最新 JSON，验证字段完整性
4. 向用户展示 Markdown 报告路径与 Top 3 摘要
5. 失败时查 `.ralph/guardrails.md`，更新 `config/selectors.yaml`，Ralph Loop 重试

## Loop 模式

| 模式 | 命令 | 场景 |
|------|------|------|
| Ralph | `/ralph-loop "修复 scraper" --completion-promise "ALL_TESTS_PASS"` | 选择器失效 |
| Fixed | `/loop 1d 复扫 {keyword} Top{N}` | 品类监控 |
| Dynamic | Captcha 后 sleep 30m 重试 | 反爬触发 |

## 关键文件

- 提示词全文：[PROMPT.md](../../PROMPT.md)
- 选择器：[config/selectors.yaml](../../config/selectors.yaml)
- 排名权重：[config/ranking.yaml](../../config/ranking.yaml)
- 进度：[.ralph/progress.md](../../.ralph/progress.md)
- 经验：[.ralph/guardrails.md](../../.ralph/guardrails.md)

## 完成信号

输出 `SOURCING_COMPLETE` 并给出 JSON/Markdown 路径。
