"""Pydantic data models for Amazon product sourcing."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class Review(BaseModel):
    review_id: Optional[str] = None
    star: Optional[float] = None
    title: Optional[str] = None
    body: Optional[str] = None
    date: Optional[str] = None
    verified_purchase: bool = False
    helpful_votes: Optional[int] = None


class Product(BaseModel):
    asin: str
    title: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = None
    price_verified: bool = False
    star_rating: Optional[float] = None
    review_count: Optional[int] = None
    bsr: Optional[int] = None
    bsr_category: Optional[str] = None
    brand: Optional[str] = None
    bullet_points: list[str] = Field(default_factory=list)
    prime_eligible: bool = False
    product_url: Optional[str] = None
    reviews: list[Review] = Field(default_factory=list)
    composite_score: Optional[float] = None
    rank: Optional[int] = None
    search_position: Optional[int] = None
    monthly_sales: Optional[int] = None
    monthly_sales_label: Optional[str] = None
    estimated_monthly_sales: Optional[int] = None
    import_score: Optional[int] = None
    import_verdict: Optional[str] = None
    import_reasons: list[str] = Field(default_factory=list)
    import_risks: list[str] = Field(default_factory=list)


class SourcingReport(BaseModel):
    query: str
    marketplace: str = "amazon.com"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    top_n: int
    products: list[Product] = Field(default_factory=list)
    total_candidates_found: int = 0
    total_candidates_analyzed: int = 0
    summary: Optional[str] = None
