"""Sync local reports into the EdgeOne bundle directory."""

from __future__ import annotations

import shutil
from pathlib import Path

from src.config import PROJECT_ROOT, get_settings

CLOUD_REPORTS_DIR = PROJECT_ROOT / "cloud-functions" / "data" / "reports"


def sync_report_to_cloud(json_path: Path) -> Path:
    """Copy one report JSON into cloud-functions/data/reports for EdgeOne deploy."""
    src = json_path.resolve()
    if not src.is_file() or src.suffix != ".json":
        raise ValueError(f"Not a report JSON file: {json_path}")

    CLOUD_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    dst = CLOUD_REPORTS_DIR / src.name
    shutil.copy2(src, dst)
    return dst


def sync_all_reports_to_cloud() -> list[str]:
    """Copy all output/*.json reports into the cloud bundle directory."""
    settings = get_settings()
    out_dir = (PROJECT_ROOT / settings["output_dir"]).resolve()
    if not out_dir.is_dir():
        return []

    synced: list[str] = []
    for src in sorted(out_dir.glob("*.json"), key=lambda p: p.stat().st_mtime):
        dst = sync_report_to_cloud(src)
        synced.append(dst.name)
    return synced
