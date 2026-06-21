"""Vercel serverless entry: handles /api/* routes."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cloud-functions"))

from app_core import create_app

app = create_app(api_prefix="/api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
