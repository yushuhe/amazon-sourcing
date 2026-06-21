"""Amazon product reviews scraper."""

from __future__ import annotations

import re

from playwright.async_api import Page

from src.browser.anti_bot import parse_rating, safe_goto
from src.config import get_selectors, get_settings
from src.models.product import Product, Review


def build_reviews_url(asin: str) -> str:
    settings = get_settings()
    return f"{settings['amazon_base_url']}/product-reviews/{asin}?sortBy=recent"


async def scrape_reviews(page: Page, product: Product, max_reviews: int = 10) -> Product:
    if max_reviews <= 0:
        return product
    selectors = get_selectors()["reviews"]
    url = build_reviews_url(product.asin)
    await safe_goto(page, url)

    items = page.locator(selectors["review_item"])
    count = await items.count()
    reviews: list[Review] = []

    for i in range(min(count, max_reviews)):
        item = items.nth(i)

        star_el = item.locator(selectors["star"]).first
        star_text = await star_el.inner_text() if await star_el.count() else None

        title_el = item.locator(selectors["title"]).first
        title = (await title_el.inner_text()).strip() if await title_el.count() else None

        body_el = item.locator(selectors["body"]).first
        body = (await body_el.inner_text()).strip() if await body_el.count() else None

        date_el = item.locator(selectors["date"]).first
        date = (await date_el.inner_text()).strip() if await date_el.count() else None

        verified_el = item.locator(selectors["verified"]).first
        verified = await verified_el.count() > 0

        helpful_el = item.locator(selectors["helpful"]).first
        helpful_text = await helpful_el.inner_text() if await helpful_el.count() else None
        helpful_votes = None
        if helpful_text:
            match = re.search(r"(\d+)", helpful_text.replace(",", ""))
            helpful_votes = int(match.group(1)) if match else None

        review_id = await item.get_attribute("id")

        reviews.append(
            Review(
                review_id=review_id,
                star=parse_rating(star_text),
                title=title,
                body=body,
                date=date,
                verified_purchase=verified,
                helpful_votes=helpful_votes,
            )
        )

    product.reviews = reviews
    return product
