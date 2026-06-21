"""Amazon search results scraper."""

from __future__ import annotations

from urllib.parse import quote_plus

from playwright.async_api import Locator, Page

from src.browser.anti_bot import (
    parse_monthly_sales,
    parse_rating,
    parse_review_count,
    safe_goto,
)
from src.config import get_selectors, get_settings
from src.models.product import Product


def build_search_url(keyword: str, page_num: int = 1) -> str:
    settings = get_settings()
    base = settings["amazon_base_url"]
    encoded = quote_plus(keyword)
    url = f"{base}/s?k={encoded}&s=exact-aware-popularity-rank"
    if page_num > 1:
        url += f"&page={page_num}"
    return url


async def _extract_monthly_sales(item: Locator, selectors: dict) -> tuple[int | None, str | None]:
    sales_el = item.locator(selectors["monthly_sales"])
    count = await sales_el.count()
    for i in range(count):
        text = await sales_el.nth(i).inner_text()
        if "bought in past month" in text.lower():
            return parse_monthly_sales(text)

    item_text = await item.inner_text()
    return parse_monthly_sales(item_text)


async def scrape_search_page(page: Page, keyword: str, page_num: int = 1) -> list[Product]:
    selectors = get_selectors()["search"]
    url = build_search_url(keyword, page_num)
    await safe_goto(page, url)

    items = page.locator(selectors["result_item"])
    count = await items.count()
    products: list[Product] = []
    seen_asins: set[str] = set()

    for i in range(count):
        item = items.nth(i)
        asin = await item.get_attribute("data-asin")
        if not asin or asin in seen_asins:
            continue
        seen_asins.add(asin)

        search_position = len(products) + 1

        title_el = item.locator(selectors["title"]).first
        title = (await title_el.inner_text()).strip() if await title_el.count() else None

        rating_el = item.locator(selectors["rating"]).first
        rating_text = await rating_el.inner_text() if await rating_el.count() else None

        review_el = item.locator(selectors["review_count"]).first
        review_text = await review_el.inner_text() if await review_el.count() else None

        monthly_sales, monthly_label = await _extract_monthly_sales(item, selectors)

        image_el = item.locator(selectors["image"]).first
        image_url = await image_el.get_attribute("src") if await image_el.count() else None

        settings = get_settings()
        product_url = f"{settings['amazon_base_url']}/dp/{asin}"

        products.append(
            Product(
                asin=asin,
                title=title,
                image_url=image_url,
                star_rating=parse_rating(rating_text),
                review_count=parse_review_count(review_text),
                product_url=product_url,
                search_position=search_position,
                monthly_sales=monthly_sales,
                monthly_sales_label=monthly_label,
                estimated_monthly_sales=monthly_sales,
            )
        )

    return products


async def scrape_search(
    page: Page,
    keyword: str,
    max_pages: int | None = None,
) -> list[Product]:
    settings = get_settings()
    pages = max_pages or settings["default_search_pages"]
    all_products: list[Product] = []
    seen: set[str] = set()

    for page_num in range(1, pages + 1):
        batch = await scrape_search_page(page, keyword, page_num)
        for product in batch:
            if product.asin not in seen:
                seen.add(product.asin)
                all_products.append(product)

        if page_num >= pages:
            break

        next_btn = page.locator(get_selectors()["search"]["next_page"])
        if await next_btn.count() == 0:
            break

    return all_products
