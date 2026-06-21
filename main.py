"""FastAPI entrypoint for Vercel and EdgeOne Pages."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_api_file = Path(__file__).parent / "cloud-functions" / "api" / "index.py"
_spec = importlib.util.spec_from_file_location("serverless_api", _api_file)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Cannot load API from {_api_file}")

_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
app = _mod.app
