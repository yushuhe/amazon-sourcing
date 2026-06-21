"""EdgeOne Cloud Functions entry (prefix /api stripped by platform)."""

from app_core import create_app

app = create_app(api_prefix="")
