"""Vercel FastAPI entrypoint (single-file for reliable serverless import)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "cloud-functions" / "data" / "reports"

SERVERLESS_SEARCH_MSG = (
    "Amazon 选品爬取依赖 Playwright，无法在 Serverless 运行。"
    "请本地执行：pip install -r requirements-dev.txt && python -m src.web"
)


class SearchRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200)
    top_n: int = Field(default=20, ge=1, le=50)
    max_reviews: int = Field(default=0, ge=0, le=30)
    pages: int = Field(default=8, ge=1, le=10)
    enrich_details: int = Field(default=0, ge=0, le=10)


def _route(prefix: str, path: str) -> str:
    p = path if path.startswith("/") else f"/{path}"
    return f"{prefix.rstrip('/')}{p}" if prefix else p


def create_app(api_prefix: str = "/api") -> FastAPI:
    application = FastAPI(title="Amazon 进货选品 API", version="1.0.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get(_route(api_prefix, "/health"))
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "runtime": "vercel",
            "reports_dir_exists": REPORTS_DIR.is_dir(),
        }

    @application.get(_route(api_prefix, "/reports"))
    async def list_reports() -> list[dict[str, str]]:
        if not REPORTS_DIR.is_dir():
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

    @application.get(_route(api_prefix, "/reports/{filename}"))
    async def get_report(filename: str) -> dict[str, Any]:
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="非法文件名")
        if not filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="仅支持 JSON 报告")
        path = (REPORTS_DIR / filename).resolve()
        if not str(path).startswith(str(REPORTS_DIR.resolve())):
            raise HTTPException(status_code=400, detail="非法路径")
        if not path.is_file():
            raise HTTPException(status_code=404, detail="报告不存在")
        return json.loads(path.read_text(encoding="utf-8"))

    @application.delete(_route(api_prefix, "/reports/{filename}"))
    async def delete_report(filename: str) -> dict[str, Any]:
        raise HTTPException(status_code=403, detail="云端演示环境不支持删除报告")

    @application.post(_route(api_prefix, "/search"))
    async def start_search(req: SearchRequest) -> None:
        raise HTTPException(status_code=503, detail=SERVERLESS_SEARCH_MSG)

    @application.get(_route(api_prefix, "/search"))
    async def search_get_hint() -> dict[str, str]:
        return {
            "detail": "请使用 POST 提交选品任务；云端 Serverless 不支持爬取，请使用本地 python -m src.web",
        }

    @application.get(_route(api_prefix, "/jobs/{job_id}"))
    async def get_job(job_id: str) -> None:
        raise HTTPException(status_code=404, detail="云端环境不支持后台任务")

    @application.exception_handler(HTTPException)
    async def http_exception_handler(_request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return application


app = create_app("/api")
