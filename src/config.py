"""Load YAML/ENV configuration."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"


def _load_dotenv() -> None:
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)


@lru_cache
def get_selectors() -> dict:
    _load_dotenv()
    with open(CONFIG_DIR / "selectors.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def get_ranking_config() -> dict:
    _load_dotenv()
    with open(CONFIG_DIR / "ranking.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_settings() -> dict:
    _load_dotenv()
    return {
        "amazon_domain": os.getenv("AMAZON_DOMAIN", "amazon.com"),
        "amazon_base_url": os.getenv("AMAZON_BASE_URL", "https://www.amazon.com"),
        "headless": os.getenv("HEADLESS", "true").lower() == "true",
        "request_delay_min": float(os.getenv("REQUEST_DELAY_MIN", "2.0")),
        "request_delay_max": float(os.getenv("REQUEST_DELAY_MAX", "5.0")),
        "max_retries": int(os.getenv("MAX_RETRIES", "3")),
        "proxy_url": os.getenv("PROXY_URL") or None,
        "default_top_n": int(os.getenv("DEFAULT_TOP_N", "20")),
        "default_max_reviews": int(os.getenv("DEFAULT_MAX_REVIEWS", "10")),
        "default_search_pages": int(os.getenv("DEFAULT_SEARCH_PAGES", "8")),
        "output_dir": Path(os.getenv("OUTPUT_DIR", "output")),
        "price_verify_concurrency": int(os.getenv("PRICE_VERIFY_CONCURRENCY", "5")),
        "price_verify_delay": float(os.getenv("PRICE_VERIFY_DELAY", "0.5")),
    }
