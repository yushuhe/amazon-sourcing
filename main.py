"""Vercel FastAPI entrypoint."""

from api_app import create_app

app = create_app("/api")
