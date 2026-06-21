"""Run sourcing pipeline in a dedicated thread with a Windows-safe event loop."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable
from typing import Optional

from src.service.sourcing import run_search

ProgressCallback = Callable[[str, int, int], None]


def _ensure_event_loop_policy() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def run_search_blocking(
    keyword: str,
    top_n: int,
    max_reviews: int,
    search_pages: int,
    enrich_details: int = 0,
    on_progress: Optional[ProgressCallback] = None,
):
    """Run async pipeline in a fresh event loop (required for Playwright on Windows + uvicorn)."""
    _ensure_event_loop_policy()
    return asyncio.run(
        run_search(
            keyword=keyword,
            top_n=top_n,
            max_reviews=max_reviews,
            search_pages=search_pages,
            enrich_details=enrich_details,
            on_progress=on_progress,
        )
    )


def format_exception(exc: BaseException) -> str:
    message = str(exc).strip()
    if message:
        return message
    name = type(exc).__name__
    if name == "NotImplementedError":
        return (
            "Playwright 无法在当前环境启动浏览器（Windows 事件循环限制）。"
            "请执行: playwright install chromium，然后重启 Web 服务。"
        )
    return name
