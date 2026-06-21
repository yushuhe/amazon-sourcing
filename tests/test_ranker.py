"""Tests for ranking and parsing logic."""

from src.browser.anti_bot import parse_monthly_sales, parse_price_from_text
from src.models.product import Product
from src.pipeline.analyzer import analyze_product
from src.pipeline.ranker import rank_from_search, rank_products


def test_parse_price_from_text():
    assert parse_price_from_text("$11.24") == 11.24
    assert parse_price_from_text("681.99") == 681.99


def test_parse_monthly_sales():
    assert parse_monthly_sales("5K+ bought in past month") == (5000, "5K+ bought in past month")
    assert parse_monthly_sales("50+ bought in past month") == (50, "50+ bought in past month")


def test_monthly_sales_ranking():
    hot = Product(asin="A1", monthly_sales=5000, search_position=5, star_rating=4.5)
    cold = Product(asin="A2", monthly_sales=50, search_position=1, star_rating=5.0)
    ranked = rank_from_search([cold, hot], top_n=2)
    assert ranked[0].asin == "A1"


def test_bsr_ranking_when_no_monthly():
    high_bsr = Product(asin="A1", bsr=50000, search_position=1, star_rating=5.0)
    low_bsr = Product(asin="A2", bsr=500, search_position=5, star_rating=4.0)
    ranked = rank_products([high_bsr, low_bsr], top_n=2)
    assert ranked[0].asin == "A2"


def test_analyzer_monthly_sales_reason():
    p = Product(asin="X", monthly_sales=3000, monthly_sales_label="3K+ bought in past month", star_rating=4.6)
    analyze_product(p, [])
    assert any("上月销量" in r for r in p.import_reasons)
