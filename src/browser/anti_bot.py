"""Anti-bot helpers: delays, retries, captcha detection."""

from __future__ import annotations

import asyncio
import random
import re
from typing import Callable, TypeVar

from playwright.async_api import Page

from src.config import get_selectors, get_settings

T = TypeVar("T")


async def random_delay() -> None:
    settings = get_settings()
    delay = random.uniform(settings["request_delay_min"], settings["request_delay_max"])
    await asyncio.sleep(delay)


async def detect_captcha(page: Page) -> bool:
    selectors = get_selectors().get("captcha_indicators", [])
    for selector in selectors:
        try:
            if selector.startswith("h4:"):
                if await page.locator(selector).count() > 0:
                    return True
            elif await page.locator(selector).count() > 0:
                return True
        except Exception:
            continue
    content = await page.content()
    return "validateCaptcha" in content or "captchacharacters" in content.lower()


async def safe_goto(page: Page, url: str) -> None:
    settings = get_settings()
    last_error: Exception | None = None

    for attempt in range(settings["max_retries"]):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await random_delay()
            if await detect_captcha(page):
                raise RuntimeError("captcha detected")
            return
        except Exception as exc:
            last_error = exc
            backoff = (2**attempt) + random.uniform(0.5, 1.5)
            await asyncio.sleep(backoff)

    raise RuntimeError(f"Failed to load {url}: {last_error}")


_PRICE_WAIT_SELECTOR = (
    "#corePriceDisplay_desktop_feature_div .priceToPay .a-offscreen, "
    ".priceToPay .a-offscreen, "
    "#price_inside_buybox .a-offscreen"
)


async def fast_goto_price(page: Page, url: str) -> None:
    """Lightweight navigation for price-only checks (no long anti-bot delay)."""
    settings = get_settings()
    settle = float(settings.get("price_verify_delay", 0.5))

    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    try:
        await page.wait_for_selector(_PRICE_WAIT_SELECTOR, timeout=8000)
    except Exception:
        pass
    await asyncio.sleep(settle)
    if await detect_captcha(page):
        raise RuntimeError("captcha detected")


def parse_rating(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"([\d.]+)\s*out of", text)
    if match:
        return float(match.group(1))
    match = re.search(r"([\d.]+)", text)
    return float(match.group(1)) if match else None


def parse_review_count(text: str | None) -> int | None:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def parse_price(whole: str | None, fraction: str | None) -> float | None:
    if not whole:
        return None
    whole_clean = re.sub(r"[^\d]", "", whole)
    frac_clean = re.sub(r"[^\d]", "", fraction or "0") or "0"
    if not whole_clean:
        return None
    return float(f"{whole_clean}.{frac_clean[:2].ljust(2, '0')}")


def parse_price_from_text(text: str | None) -> float | None:
    """Parse price from strings like '$11.24' or '11.24'."""
    if not text:
        return None
    cleaned = text.strip().replace(",", "")
    match = re.search(r"\$?\s*([\d]+)\.(\d{2})", cleaned)
    if match:
        return float(f"{match.group(1)}.{match.group(2)}")
    match = re.search(r"\$?\s*([\d]+)", cleaned)
    if match:
        return float(match.group(1))
    return None


def parse_monthly_sales(text: str | None) -> tuple[int | None, str | None]:
    """
    Parse Amazon 'bought in past month' text.
    Examples: '5K+ bought in past month', '50+ bought in past month'
    """
    if not text:
        return None, None
    match = re.search(
        r"([\d,.]+)\s*([KkMm])?\s*\+\s*bought in past month",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None, None

    num = float(match.group(1).replace(",", ""))
    suffix = (match.group(2) or "").upper()
    if suffix == "K":
        num *= 1000
    elif suffix == "M":
        num *= 1_000_000
    return int(num), match.group(0).strip()


def parse_bsr(text: str) -> tuple[int | None, str | None]:
    match = re.search(r"#([\d,]+)\s+in\s+(.+?)(?:\s*\(|$|\[)", text, re.IGNORECASE)
    if match:
        bsr = int(match.group(1).replace(",", ""))
        category = match.group(2).strip().rstrip(")")
        return bsr, category
    match = re.search(r"Best Sellers Rank:\s*#([\d,]+)\s+in\s+(.+)", text, re.IGNORECASE)
    if match:
        return int(match.group(1).replace(",", "")), match.group(2).strip()
    return None, None
