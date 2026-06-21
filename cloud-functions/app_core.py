"""Shared serverless FastAPI app for Vercel and EdgeOne."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

SERVERLESS_SEARCH_MSG = (
    "Amazon 选品爬取依赖 Playwright 浏览器自动化，无法在 Serverless 环境运行。"
    "请在本地启动：pip install -r requirements-dev.txt && python -m src.web"
)

# Resolve reports relative to cloud-functions/ (works on Vercel and EdgeOne)
REPORTS_DIR = Path(__file__).resolve().parent / "data" / "reports"


class SearchRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200)
    top_n: int = Field(default=20, ge=1, le=50)
    max_reviews: int = Field(default=0, ge=0, le=30)
    pages: int = Field(default=8, ge=1, le=10)
    enrich_details: int = Field(default=0, ge=0, le=10)


def _route(prefix: str, path: str) -> str:
    p = path if path.startswith("/") else f"/{path}"
    if not prefix:
        return p
    return f"{prefix.rstrip('/')}{p}"


def _validate_report_filename(filename: str) -> str:
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="非法文件名")
    if not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="仅支持 JSON 报告")
    return filename


def _report_path(filename: str) -> Path:
    filename = _validate_report_filename(filename)
    path = (REPORTS_DIR / filename).resolve()
    reports_root = REPORTS_DIR.resolve()
    if not str(path).startswith(str(reports_root)):
        raise HTTPException(status_code=400, detail="非法路径")
    return path


def create_app(api_prefix: str = "") -> FastAPI:
    """Create FastAPI app. Use api_prefix='/api' on Vercel, '' on EdgeOne."""
    app = FastAPI(title="Amazon 进货选品 API", version="1.0.0")

    @app.get(_route(api_prefix, "/health"))
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "runtime": "serverless",
            "reports_dir_exists": REPORTS_DIR.exists(),
        }

    @app.get(_route(api_prefix, "/reports"))
    async def list_reports() -> list[dict[str, str]]:
        if not REPORTS_DIR.exists():
            return []
        reports = []
        for path in sorted(REPORTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            reports.append(
                {
                    "filename": path.name,
                    "query": path.stem.rsplit("_", 2)[0] if "_" in path.stem else path.stem,
                    "modified": datetime.fromtimestamp(
                        path.stat().st_mtime, tz=timezone.utc
                    ).isoformat(),
                }
            )
        return reports[:20]

    @app.get(_route(api_prefix, "/reports/{filename}"))
    async def get_report(filename: str) -> dict[str, Any]:
        path = _report_path(filename)
        if not path.exists():
            raise HTTPException(status_code=404, detail="报告不存在")
        return json.loads(path.read_text(encoding="utf-8"))

    @app.delete(_route(api_prefix, "/reports/{filename}"))
    async def delete_report(filename: str) -> dict[str, Any]:
        raise HTTPException(status_code=403, detail="云端演示环境不支持删除报告，请使用本地服务")

    @app.post(_route(api_prefix, "/search"))
    async def start_search(req: SearchRequest) -> None:
        raise HTTPException(status_code=503, detail=SERVERLESS_SEARCH_MSG)

    @app.get(_route(api_prefix, "/search"))
    async def search_get_hint() -> dict[str, str]:
        return {
            "detail": "请使用 POST 提交选品任务；云端 Serverless 不支持爬取，请使用本地 python -m src.web",
        }

    @app.get(_route(api_prefix, "/jobs/{job_id}"))
    async def get_job(job_id: str) -> None:
        raise HTTPException(status_code=404, detail="云端环境不支持后台任务，请使用本地服务运行选品")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return app
