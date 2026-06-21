"""Shared sourcing pipeline used by CLI and Web API."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Optional

from src.browser.context import browser_session
from src.models.product import SourcingReport
from src.pipeline.analyzer import analyze_report
from src.pipeline.exporter import export_report
from src.pipeline.ranker import rank_from_search, rank_products
from src.scrapers.product import scrape_product
from src.scrapers.reviews import scrape_reviews
from src.scrapers.search import scrape_search

ProgressCallback = Callable[[str, int, int], None]


async def run_search(
    keyword: str,
    top_n: int,
    max_reviews: int,
    search_pages: int,
    enrich_details: int = 0,
    on_progress: Optional[ProgressCallback] = None,
) -> tuple[SourcingReport, tuple[Path, Path]]:
    def progress(message: str, current: int = 0, total: int = 0) -> None:
        if on_progress:
            on_progress(message, current, total)

    async with browser_session() as (_, __, page):
        progress(f"正在扫描「{keyword}」搜索页（共 {search_pages} 页）...", 0, 1)
        products = await scrape_search(page, keyword, max_pages=search_pages)
        total_found = len(products)

        if total_found == 0:
            report = SourcingReport(
                query=keyword,
                top_n=top_n,
                total_candidates_found=0,
                total_candidates_analyzed=0,
                summary="未找到商品，请增加扫描页数或更换关键词。",
            )
            paths = export_report(report)
            progress("完成（无结果）", 0, 0)
            return report, paths

        progress(f"共 {total_found} 个商品，按上月销量排名...", 0, 0)
        ranked = rank_from_search(products, top_n=top_n)

        detail_count = min(enrich_details, len(ranked))
        if detail_count > 0:
            progress(f"仅对前 {detail_count} 名补充 BSR/详情（可选）...", 0, detail_count)
            enriched: list = []
            for idx, product in enumerate(ranked[:detail_count], start=1):
                progress(f"补充详情 #{idx}: {product.asin}", idx, detail_count)
                try:
                    product = await scrape_product(page, product)
                    if max_reviews > 0:
                        product = await scrape_reviews(page, product, max_reviews=max_reviews)
                except Exception as exc:
                    progress(f"警告: {product.asin} 详情补充失败 ({exc})", idx, detail_count)
                enriched.append(product)
            ranked[:detail_count] = enriched
            if any(p.bsr for p in enriched):
                ranked = rank_products(ranked, top_n=top_n)

        report = SourcingReport(
            query=keyword,
            top_n=top_n,
            products=ranked,
            total_candidates_found=total_found,
            total_candidates_analyzed=total_found if enrich_details == 0 else detail_count,
        )
        report = analyze_report(report, fast_mode=(enrich_details == 0))
        paths = export_report(report)
        progress("完成", 1, 1)
        return report, paths
