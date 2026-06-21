"""Re-export for local tooling."""

import sys
from pathlib import Path

from api.index import app

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cloud-functions"))
from app_core import create_app

__all__ = ["app", "create_app"]
