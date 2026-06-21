"""Sync local reports and redeploy to EdgeOne Pages."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.service.cloud_sync import sync_all_reports_to_cloud


def main() -> None:
    synced = sync_all_reports_to_cloud()
    if synced:
        print(f"Synced {len(synced)} report(s) to cloud-functions/data/reports/")
        for name in synced[-10:]:
            print(f"  - {name}")
    else:
        print("No reports in output/ — run a local search first (python -m src.web).")

    env = os.environ.copy()
    env["PAGES_SOURCE"] = "skills"
    print("\nDeploying to EdgeOne...")
    subprocess.run(
        ["edgeone", "pages", "deploy"],
        cwd=ROOT,
        env=env,
        check=True,
    )


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
    except FileNotFoundError:
        raise SystemExit("edgeone CLI not found. Install: npm install -g edgeone@latest") from None
