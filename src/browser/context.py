"""Playwright browser context with anti-bot settings."""

from __future__ import annotations

import random
import shutil
from contextlib import asynccontextmanager
from typing import AsyncIterator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from src.config import get_settings

USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
        "Gecko/20100101 Firefox/125.0"
    ),
]


def _chrome_available() -> bool:
    """Detect if Google Chrome is installed."""
    if shutil.which("chrome") or shutil.which("google-chrome"):
        return True
    from pathlib import Path

    chrome_paths = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ]
    return any(p.exists() for p in chrome_paths)


def _edge_available() -> bool:
    if shutil.which("msedge"):
        return True
    from pathlib import Path

    edge_paths = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ]
    return any(p.exists() for p in edge_paths)


async def _launch_browser(playwright, launch_args: dict):
    """Try bundled Chromium, then system Chrome, then Edge."""
    errors: list[str] = []

    try:
        return await playwright.chromium.launch(**launch_args)
    except Exception as exc:
        errors.append(f"bundled: {exc}")

    if _chrome_available():
        try:
            return await playwright.chromium.launch(channel="chrome", **launch_args)
        except Exception as exc:
            errors.append(f"chrome: {exc}")

    if _edge_available():
        try:
            return await playwright.chromium.launch(channel="msedge", **launch_args)
        except Exception as exc:
            errors.append(f"msedge: {exc}")

    raise RuntimeError(
        "无法启动浏览器。请任选其一：\n"
        "1) 运行 playwright install chromium\n"
        "2) 确保已安装 Google Chrome 或 Microsoft Edge\n"
        f"详情: {'; '.join(errors)}"
    )


@asynccontextmanager
async def browser_session() -> AsyncIterator[tuple[Browser, BrowserContext, Page]]:
    settings = get_settings()
    async with async_playwright() as playwright:
        launch_args = {
            "headless": settings["headless"],
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if settings["proxy_url"]:
            launch_args["proxy"] = {"server": settings["proxy_url"]}

        browser = await _launch_browser(playwright, launch_args)
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            locale="en-US",
            viewport={"width": 1366, "height": 768},
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page = await context.new_page()
        try:
            yield browser, context, page
        finally:
            await context.close()
            await browser.close()
