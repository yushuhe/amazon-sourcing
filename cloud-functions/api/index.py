"""Shared FastAPI API for cloud deployment (Vercel / EdgeOne)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Amazon 进货选品 API", version="1.0.0")

REPORTS_DIR = Path(__file__).resolve().parent.parent / "data" / "reports"

SERVERLESS_SEARCH_MSG = (
    "Amazon 选品爬取依赖 Playwright 浏览器自动化，无法在 Serverless 环境运行。"
    "请在本地启动完整服务：pip install -r requirements-dev.txt && python -m src.web"
)


def api_path(relative: str) -> str:
    """EdgeOne strips /api prefix; Vercel keeps the full path."""
    rel = relative if relative.startswith("/") else f"/{relative}"
    if os.getenv("VERCEL"):
        return f"/api{rel}"
    return rel


class SearchRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200)
    top_n: int = Field(default=20, ge=1, le=50)
    max_reviews: int = Field(default=0, ge=0, le=30)
    pages: int = Field(default=8, ge=1, le=10)
    enrich_details: int = Field(default=0, ge=0, le=10)


def _validate_report_filename(filename: str) -> str:
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="非法文件名")
    if not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="仅支持 JSON 报告")
    return filename


def _report_path(filename: str) -> Path:
    filename = _validate_report_filename(filename)
    path = (REPORTS_DIR / filename).resolve()
    if not str(path).startswith(str(REPORTS_DIR.resolve())):
        raise HTTPException(status_code=400, detail="非法路径")
    return path


@app.get(api_path("/health"))
async def health() -> dict[str, str]:
    return {"status": "ok", "runtime": "serverless"}


@app.get(api_path("/reports"))
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


@app.get(api_path("/reports/{filename}"))
async def get_report(filename: str) -> dict[str, Any]:
    path = _report_path(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="报告不存在")
    return json.loads(path.read_text(encoding="utf-8"))


@app.delete(api_path("/reports/{filename}"))
async def delete_report(filename: str) -> dict[str, Any]:
    raise HTTPException(status_code=403, detail="云端演示环境不支持删除报告，请使用本地服务")


@app.post(api_path("/search"))
async def start_search(req: SearchRequest) -> None:
    raise HTTPException(status_code=503, detail=SERVERLESS_SEARCH_MSG)


@app.get(api_path("/jobs/{job_id}"))
async def get_job(job_id: str) -> None:
    raise HTTPException(status_code=404, detail="云端环境不支持后台任务，请使用本地服务运行选品")


@app.exception_handler(HTTPException)
async def http_exception_handler(_request, exc: HTTPException):
    detail: Any = exc.detail
    return JSONResponse(status_code=exc.status_code, content={"detail": detail})
