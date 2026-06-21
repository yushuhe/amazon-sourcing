"""Import recommendation analysis for sourcing decisions."""

from __future__ import annotations

from src.models.product import Product, SourcingReport


def estimate_monthly_sales(bsr: int | None) -> int | None:
    """Rough BSR-to-monthly-units estimate (industry rule-of-thumb)."""
    if not bsr or bsr <= 0:
        return None
    if bsr <= 100:
        return 5000
    if bsr <= 500:
        return 2000
    if bsr <= 2000:
        return 800
    if bsr <= 10000:
        return 200
    if bsr <= 50000:
        return 50
    return 15


def analyze_product(product: Product, peer_bsrs: list[int]) -> Product:
    reasons: list[str] = []
    risks: list[str] = []
    score = 50

    product.estimated_monthly_sales = product.monthly_sales or estimate_monthly_sales(product.bsr)

    if product.monthly_sales and product.monthly_sales > 0:
        label = product.monthly_sales_label or f"{product.monthly_sales}+ bought in past month"
        reasons.append(f"上月销量 {label}，Amazon 官方近期购买数据")
        if product.monthly_sales >= 5000:
            score += 30
        elif product.monthly_sales >= 1000:
            score += 22
        elif product.monthly_sales >= 200:
            score += 15
        elif product.monthly_sales >= 50:
            score += 8
        else:
            score += 3

        if peer_bsrs and product.monthly_sales:
            pass  # peer comparison uses monthly in rank already
    elif product.bsr:
        if product.bsr <= 500:
            reasons.append(f"类目 BSR #{product.bsr:,}，属于该品类销量第一梯队")
            score += 25
        elif product.bsr <= 2000:
            reasons.append(f"类目 BSR #{product.bsr:,}，销量表现靠前")
            score += 18
        elif product.bsr <= 10000:
            reasons.append(f"类目 BSR #{product.bsr:,}，有一定市场基础")
            score += 8
        else:
            risks.append(f"BSR #{product.bsr:,} 偏后，动销可能较慢")
            score -= 10

        if peer_bsrs:
            better_than = sum(1 for b in peer_bsrs if b > product.bsr) / len(peer_bsrs)
            if better_than >= 0.7:
                reasons.append(f"在本次 {len(peer_bsrs)} 个候选中，销量排名前 {int(better_than * 100)}%")
                score += 10
    elif product.search_position:
        pos = product.search_position
        if pos <= 10:
            reasons.append(f"搜索热度排名第 {pos} 位（Amazon 按销量/热度排序）")
            score += 20
        elif pos <= 30:
            reasons.append(f"搜索热度排名第 {pos} 位，处于品类前排")
            score += 12
        elif pos <= 60:
            reasons.append(f"搜索热度排名第 {pos} 位，有一定曝光")
            score += 5
        else:
            risks.append(f"搜索排名第 {pos} 位偏后，热度一般")
            score -= 5
    else:
        risks.append("缺少销量排名数据")
        score -= 5

    rating = product.star_rating or 0
    reviews = product.review_count or 0

    if rating >= 4.5 and reviews >= 200:
        reasons.append(f"评分 {rating} + {reviews:,} 条评论，口碑经过市场验证")
        score += 15
    elif rating >= 4.0:
        reasons.append(f"评分 {rating}，口碑尚可")
        score += 5
    elif rating > 0:
        risks.append(f"评分仅 {rating}，差评风险需关注")
        score -= 15

    if 100 <= reviews <= 3000:
        reasons.append("评论数适中：有市场验证，竞争尚未过度红海")
        score += 10
    elif reviews > 15000:
        risks.append(f"已有 {reviews:,} 条评论，大品牌/红海概率高，新入场难度大")
        score -= 12
    elif 0 < reviews < 50:
        reasons.append("评论较少，可能是新品或小众款，有机会但风险也高")
        score += 3

    if product.prime_eligible:
        reasons.append("支持 Prime，物流体验好、转化通常更高")
        score += 3

    if product.reviews:
        avg_recent = sum(r.star or 0 for r in product.reviews) / len(product.reviews)
        if avg_recent >= 4.5:
            reasons.append(f"最近 {len(product.reviews)} 条评论均分 {avg_recent:.1f}，近期口碑稳定")
            score += 5
        elif avg_recent < 3.5:
            risks.append(f"最近评论均分仅 {avg_recent:.1f}，可能存在质量/描述问题")
            score -= 10

    score = max(0, min(100, score))
    product.import_score = score

    if score >= 75:
        product.import_verdict = "强烈推荐进货"
    elif score >= 55:
        product.import_verdict = "可考虑进货"
    elif score >= 40:
        product.import_verdict = "谨慎观察"
    else:
        product.import_verdict = "不建议进货"

    product.import_reasons = reasons[:6]
    product.import_risks = risks[:4]
    return product


def build_report_summary(report: SourcingReport, fast_mode: bool = False) -> str:
    if not report.products:
        return "未找到可对比商品，请增加扫描页数或更换关键词。"

    top = report.products[0]
    bsrs = [p.bsr for p in report.products if p.bsr]

    if fast_mode:
        lines = [
            f"从 {report.total_candidates_found} 个同类商品中，",
            f"按上月销量（bought in past month）排出前 {len(report.products)} 名。",
        ]
    else:
        lines = [
            f"从 {report.total_candidates_found} 个同类候选中，",
            f"排出前 {len(report.products)} 名。",
        ]
    if top.title:
        lines.append(f"榜首：{top.title[:60]}…（{top.import_verdict}，进货指数 {top.import_score}）")
    if bsrs:
        lines.append(f"BSR 范围 #{min(bsrs):,} ~ #{max(bsrs):,}。")

    strong = sum(1 for p in report.products if (p.import_score or 0) >= 75)
    lines.append(f"其中 {strong} 款达到「强烈推荐进货」标准。")
    return " ".join(lines)


def analyze_report(report: SourcingReport, fast_mode: bool = False) -> SourcingReport:
    peer_bsrs = [p.bsr for p in report.products if p.bsr]
    for product in report.products:
        analyze_product(product, peer_bsrs)
    report.summary = build_report_summary(report, fast_mode=fast_mode)
    return report
