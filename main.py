"""Compatibility shim; Vercel entrypoint is api/index.py."""

from api.index import app

__all__ = ["app"]
