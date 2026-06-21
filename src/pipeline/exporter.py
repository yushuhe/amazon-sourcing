"""Export sourcing report to JSON and Markdown."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Template

from src.config import PROJECT_ROOT, get_settings
from src.models.product import SourcingReport

MARKDOWN_TEMPLATE = Template(
    """# Amazon 进货选品报告

- **关键词/品类**: {{ report.query }}
- **站点**: {{ report.marketplace }}
- **生成时间**: {{ report.generated_at.isoformat() }}
- **输出 Top N**: {{ report.top_n }}
- **扫描候选数**: {{ report.total_candidates_found }}
- **深度分析数**: {{ report.total_candidates_analyzed }}

> {{ report.summary or '' }}

## 对比总览（按类目销量 BSR 排名）

| 排名 | 商品 | 上月销量 | BSR | 评分 | 评论数 | 进货指数 | 结论 |
|------|------|----------|-----|------|--------|----------|------|
{% for p in report.products -%}
| {{ p.rank }} | {{ (p.title or p.asin)[:40] }} | {% if p.monthly_sales_label %}{{ p.monthly_sales_label }}{% elif p.monthly_sales %}{{ p.monthly_sales }}+{% else %}-{% endif %} | {% if p.bsr %}#{{ p.bsr }}{% else %}-{% endif %} | {{ p.star_rating or '-' }} | {{ p.review_count or '-' }} | {{ p.import_score or '-' }} | {{ p.import_verdict or '-' }} |
{% endfor %}

---

{% for product in report.products %}
## #{{ product.rank }} {{ product.title or product.asin }}

**{{ product.import_verdict or '' }}** · 进货指数 {{ product.import_score or '-' }}/100 · 预估月销 {% if product.estimated_monthly_sales %}{{ product.estimated_monthly_sales }}+ 件{% else %}未知{% endif %}

![{{ product.title or product.asin }}]({{ product.image_url or '' }})

| 字段 | 值 |
|------|-----|
| ASIN | {{ product.asin }} |
| 评分 | {{ product.star_rating or 'N/A' }} |
| 评论数 | {{ product.review_count or 'N/A' }} |
| BSR | {% if product.bsr %}#{{ product.bsr }} in {{ product.bsr_category or 'Unknown' }}{% else %}N/A{% endif %} |
| Prime | {{ 'Yes' if product.prime_eligible else 'No' }} |
| 链接 | [查看商品]({{ product.product_url }}) |

{% if product.import_reasons %}
**值得进货的理由:**
{% for r in product.import_reasons %}
- ✅ {{ r }}
{% endfor %}
{% endif %}

{% if product.import_risks %}
**风险提示:**
{% for r in product.import_risks %}
- ⚠️ {{ r }}
{% endfor %}
{% endif %}

{% if product.bullet_points %}
**卖点:**
{% for point in product.bullet_points %}
- {{ point }}
{% endfor %}
{% endif %}

{% if product.reviews %}
**买家评论摘录 ({{ product.reviews|length }} 条):**
{% for review in product.reviews %}
- ⭐ {{ review.star or '?' }}/5 — **{{ review.title or '无标题' }}** ({{ review.date or '' }}{% if review.verified_purchase %}, Verified{% endif %})
  > {{ review.body or '' }}
{% endfor %}
{% endif %}

---

{% endfor %}
"""
)


def _slugify(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text).strip("_")[:60]


def export_report(report: SourcingReport, output_dir: Path | None = None) -> tuple[Path, Path]:
    settings = get_settings()
    out_dir = output_dir or (PROJECT_ROOT / settings["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    slug = _slugify(report.query)
    json_path = out_dir / f"{slug}_{timestamp}.json"
    md_path = out_dir / f"{slug}_{timestamp}.md"

    for product in report.products:
        product.price = None
        product.price_verified = False

    json_path.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    md_path.write_text(
        MARKDOWN_TEMPLATE.render(report=report),
        encoding="utf-8",
    )
    return json_path, md_path
