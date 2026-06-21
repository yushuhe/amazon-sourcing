"""Amazon product detail page scraper."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Optional

from playwright.async_api import BrowserContext, Page

from src.browser.anti_bot import (
    fast_goto_price,
    parse_bsr,
    parse_monthly_sales,
    parse_price,
    parse_price_from_text,
    parse_rating,
    parse_review_count,
    safe_goto,
)
from src.config import get_selectors, get_settings
from src.models.product import Product

# Buy-box price selectors in priority order (first match wins — do NOT min all prices)
_BUYBOX_PRICE_SELECTORS = [
    "#corePriceDisplay_desktop_feature_div .priceToPay .a-offscreen",
    "#corePriceDisplay_desktop_feature_div .a-price:not(.a-text-price) .a-offscreen",
    ".priceToPay .a-offscreen",
    "#price_inside_buybox .a-offscreen",
    "#corePrice_feature_div .priceToPay .a-offscreen",
    "#apex_desktop .a-price:not(.a-text-price) .a-offscreen",
    "#tp_price_block_total_price_ingress .a-offscreen",
    "#sns-base-price .a-offscreen",
]


def _product_url(asin: str, price_only: bool = False) -> str:
    settings = get_settings()
    base = f"{settings['amazon_base_url']}/dp/{asin}"
    if price_only:
        return f"{base}?th=1&psc=1"
    return base


async def _extract_buybox_price(page: Page, selectors: dict | None = None) -> float | None:
    """Extract the main buy-box price (matches what user sees on product page)."""
    for selector in _BUYBOX_PRICE_SELECTORS:
        el = page.locator(selector).first
        if await el.count():
            price = parse_price_from_text(await el.inner_text())
            if price and 0.01 <= price <= 50_000:
                return price

    if selectors:
        whole_el = page.locator(selectors["price_whole"]).first
        frac_el = page.locator(selectors["price_fraction"]).first
        if await whole_el.count():
            price = parse_price(
                await whole_el.inner_text(),
                await frac_el.inner_text() if await frac_el.count() else None,
            )
            if price and 0.01 <= price <= 50_000:
                return price

    return None


async def scrape_price_only(page: Page, product: Product, *, fast: bool = False) -> Product:
    """Visit official product page and read buy-box price only."""
    url = _product_url(product.asin, price_only=True)
    if fast:
        await fast_goto_price(page, url)
    else:
        await safe_goto(page, url)

    price = await _extract_buybox_price(page)
    if price:
        product.price = price
        product.price_verified = True
    product.product_url = url
    return product


ProgressCallback = Callable[[str, int, int], None]


async def verify_prices_parallel(
    context: BrowserContext,
    products: list[Product],
    on_progress: Optional[ProgressCallback] = None,
) -> list[Product]:
    """Verify buy-box prices concurrently (multiple tabs)."""
    settings = get_settings()
    concurrency = max(1, settings["price_verify_concurrency"])
    sem = asyncio.Semaphore(concurrency)
    completed = 0
    lock = asyncio.Lock()
    total = len(products)

    async def verify_one(product: Product) -> Product:
        nonlocal completed
        async with sem:
            page = await context.new_page()
            try:
                return await scrape_price_only(page, product, fast=True)
            except Exception:
                return product
            finally:
                await page.close()
                async with lock:
                    completed += 1
                    if on_progress:
                        on_progress(
                            f"批量核验官网价格 {completed}/{total}（{concurrency} 路并发）",
                            completed,
                            total,
                        )

    return list(await asyncio.gather(*[verify_one(p) for p in products]))


async def scrape_product(page: Page, product: Product) -> Product:
    selectors = get_selectors()["product"]
    url = _product_url(product.asin)
    await safe_goto(page, url)

    title_el = page.locator(selectors["title"]).first
    if await title_el.count():
        product.title = (await title_el.inner_text()).strip()

    rating_el = page.locator(selectors["rating"]).first
    if await rating_el.count():
        product.star_rating = parse_rating(await rating_el.inner_text())

    review_el = page.locator(selectors["review_count"]).first
    if await review_el.count():
        product.review_count = parse_review_count(await review_el.inner_text())

    price = await _extract_buybox_price(page, selectors)
    if price:
        product.price = price
        product.price_verified = True

    page_text = await page.inner_text("body")
    monthly_sales, monthly_label = parse_monthly_sales(page_text)
    if monthly_sales:
        product.monthly_sales = monthly_sales
        product.monthly_sales_label = monthly_label
        product.estimated_monthly_sales = monthly_sales

    image_el = page.locator(selectors["main_image"]).first
    if await image_el.count():
        product.image_url = (
            await image_el.get_attribute("src")
            or await image_el.get_attribute("data-old-hires")
            or product.image_url
        )

    bullets = page.locator(selectors["bullet_points"])
    bullet_count = await bullets.count()
    product.bullet_points = []
    for i in range(min(bullet_count, 10)):
        text = (await bullets.nth(i).inner_text()).strip()
        if text:
            product.bullet_points.append(text)

    bsr_el = page.locator(selectors["bsr_section"]).first
    if await bsr_el.count():
        bsr_text = await bsr_el.inner_text()
        bsr, category = parse_bsr(bsr_text)
        product.bsr = bsr
        product.bsr_category = category
        if not product.estimated_monthly_sales:
            from src.pipeline.analyzer import estimate_monthly_sales

            product.estimated_monthly_sales = estimate_monthly_sales(bsr)

    prime_el = page.locator(selectors["prime_badge"]).first
    product.prime_eligible = await prime_el.count() > 0

    product.product_url = url
    return product
