# Guardrails — Amazon Scraper 经验沉淀

> Agent 在 Loop 迭代中遇到失败时，在此记录原因与解决方案，避免重复犯错。

## 通用原则

1. **选择器外置**：所有 CSS 选择器只在 `config/selectors.yaml` 修改
2. **请求频率**：REQUEST_DELAY_MIN 不低于 2.0 秒
3. **Captcha 处理**：连续 2 次 Captcha → 停止并建议配置 PROXY_URL
4. **BSR 缺失**：使用 review_count * star_rating 降级排名

## 已知问题

| 日期 | 问题 | 解决方案 |
|------|------|----------|
| 2026-06-21 | Amazon 搜索页 DOM 可能随地区/登录状态变化 | 优先使用 `[data-component-type="s-search-result"]` + `data-asin` |
| 2026-06-21 | 详情页 BSR 位于多个可能的 section | 使用 `#detailBulletsWrapper_feature_div` 等组合选择器 + 正则解析 |
| 2026-06-21 | 评论页需按 ASIN 访问 `/product-reviews/{asin}` | 使用 `sortBy=recent` 获取最新评论 |

## 禁止事项

- 勿在同一 IP 短时间发起大量请求
- 勿硬编码选择器到 Python 文件
- 勿将 `.env` 或代理密码提交到 git

## 模板（Loop 迭代时追加）

```
### YYYY-MM-DD — {简短描述}
- **触发**: {URL 或 操作}
- **错误**: {错误信息}
- **修复**: {具体改动}
- **验证**: {pytest / CLI 命令}
```
