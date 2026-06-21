"""Vercel FastAPI entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

# Make cloud-functions importable without importlib
sys.path.insert(0, str(Path(__file__).resolve().parent / "cloud-functions"))

from app_core import create_app

app = create_app(api_prefix="/api")
