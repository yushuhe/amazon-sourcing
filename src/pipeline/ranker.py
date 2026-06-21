"""Product ranking by monthly sales, BSR, and quality signals."""

from __future__ import annotations

import math

from src.config import get_ranking_config
from src.models.product import Product


def _sales_score(bsr: int | None, review_count: int | None, star_rating: float | None) -> float:
    cfg = get_ranking_config()
    if bsr and bsr > 0:
        return 1.0 / math.log10(bsr + 10)

    if cfg.get("fallback", {}).get("use_review_rating_fallback") and review_count and star_rating:
        return min((review_count * star_rating) / 50000.0, 1.0)

    return 0.0


def compute_composite_score(product: Product) -> float:
    cfg = get_ranking_config()
    weights = cfg.get("weights", {})
    cap = cfg.get("review_confidence_cap", 1000)

    if product.monthly_sales and product.monthly_sales > 0:
        sales = min(math.log10(product.monthly_sales + 1) / 4.0, 1.0)
    else:
        sales = _sales_score(product.bsr, product.review_count, product.star_rating)

    rating = (product.star_rating or 0.0) / 5.0
    review_conf = min((product.review_count or 0) / cap, 1.0)

    score = (
        weights.get("sales", 0.5) * sales
        + weights.get("rating", 0.3) * rating
        + weights.get("review_confidence", 0.2) * review_conf
    )
    return round(score, 4)


def _monthly_sales_rank_key(product: Product) -> tuple:
    """Primary: last-month sales (higher first). Fallback: search position."""
    sales = product.monthly_sales or product.estimated_monthly_sales or 0
    if sales > 0:
        return (0, -sales, -(product.star_rating or 0.0), product.search_position or 9999)
    return (1, product.search_position or 9999, -(product.review_count or 0))


def _bsr_rank_key(product: Product) -> tuple:
    bsr = product.bsr if product.bsr and product.bsr > 0 else 99_999_999
    return (bsr, -(product.star_rating or 0.0), -(product.review_count or 0))


def rank_from_search(products: list[Product], top_n: int) -> list[Product]:
    """Rank by Amazon 'bought in past month' when available, else search position."""
    ranked = sorted(products, key=_monthly_sales_rank_key)

    result: list[Product] = []
    for idx, product in enumerate(ranked[:top_n], start=1):
        product.rank = idx
        product.composite_score = compute_composite_score(product)
        result.append(product)
    return result


def rank_products(products: list[Product], top_n: int) -> list[Product]:
    has_monthly = any(p.monthly_sales and p.monthly_sales > 0 for p in products)
    has_bsr = any(p.bsr and p.bsr > 0 for p in products)

    if has_monthly:
        key_fn = _monthly_sales_rank_key
    elif has_bsr:
        key_fn = _bsr_rank_key
    else:
        key_fn = _monthly_sales_rank_key

    for product in products:
        product.composite_score = compute_composite_score(product)

    ranked = sorted(products, key=key_fn)
    result: list[Product] = []
    for idx, product in enumerate(ranked[:top_n], start=1):
        product.rank = idx
        result.append(product)
    return result
