"""CLI entry point for Amazon product sourcing."""

from __future__ import annotations

import asyncio

import typer

from src.config import get_settings
from src.service.sourcing import run_search

app = typer.Typer(help="Amazon 进货选品 CLI")


@app.command()
def search(
    keyword: str = typer.Argument(..., help="商品类别或搜索关键词"),
    top: int = typer.Option(None, "--top", "-n", help="输出 Top N 商品"),
    max_reviews: int = typer.Option(0, "--max-reviews", "-r", help="补充详情时抓取评论数，0=不抓"),
    pages: int = typer.Option(None, "--pages", "-p", help="搜索扫描页数"),
    enrich: int = typer.Option(0, "--enrich", "-e", help="对前 N 名补充详情页 BSR，0=快速模式"),
) -> None:
    """按关键词搜索 Amazon 并输出进货推荐报告。"""
    settings = get_settings()
    top_n = top or settings["default_top_n"]
    reviews = max_reviews if max_reviews is not None else 0
    search_pages = pages or settings["default_search_pages"]

    report, (json_path, md_path) = asyncio.run(
        run_search(
            keyword,
            top_n,
            reviews,
            search_pages,
            enrich_details=enrich,
            on_progress=lambda msg, cur, tot: typer.echo(msg),
        )
    )
    typer.echo(f"\nSOURCING_COMPLETE")
    typer.echo(f"JSON: {json_path}")
    typer.echo(f"Markdown: {md_path}")
    typer.echo(f"Top {len(report.products)} products ranked by composite score")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
