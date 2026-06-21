"""FastAPI web application for Amazon sourcing."""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.config import PROJECT_ROOT, get_settings
from src.service.runner import format_exception, run_search_blocking

app = FastAPI(title="Amazon 进货选品", version="1.0.0")

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_jobs_lock = threading.Lock()


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SearchRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=200, description="商品类别或关键词")
    top_n: int = Field(default=20, ge=1, le=50, description="输出品类内前 N 名")
    max_reviews: int = Field(default=0, ge=0, le=30, description="补充详情时抓取评论数，0=不抓")
    pages: int = Field(default=8, ge=1, le=10, description="搜索扫描页数")
    enrich_details: int = Field(default=0, ge=0, le=10, description="对前几名补充详情页，0=快速模式")


class JobInfo(BaseModel):
    job_id: str
    status: JobStatus
    message: str = ""
    progress_current: int = 0
    progress_total: int = 0
    keyword: str = ""
    created_at: str = ""
    completed_at: Optional[str] = None
    report: Optional[dict[str, Any]] = None
    json_path: Optional[str] = None
    md_path: Optional[str] = None
    error: Optional[str] = None


_jobs: dict[str, JobInfo] = {}


def _output_dir() -> Path:
    settings = get_settings()
    out = PROJECT_ROOT / settings["output_dir"]
    out.mkdir(parents=True, exist_ok=True)
    return out


def _validate_report_filename(filename: str) -> str:
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="非法文件名")
    if not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="仅支持删除 JSON 报告")
    return filename


def _report_json_path(filename: str) -> Path:
    path = (_output_dir() / filename).resolve()
    if not str(path).startswith(str(_output_dir().resolve())):
        raise HTTPException(status_code=400, detail="非法路径")
    return path


def _update_job(job_id: str, **kwargs: Any) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job:
            for key, value in kwargs.items():
                setattr(job, key, value)


async def _execute_job(job_id: str, req: SearchRequest) -> None:
    _update_job(job_id, status=JobStatus.RUNNING, message="启动浏览器...")

    def on_progress(message: str, current: int, total: int) -> None:
        _update_job(
            job_id,
            message=message,
            progress_current=current,
            progress_total=total,
        )

    try:
        report, (json_path, md_path) = await asyncio.to_thread(
            run_search_blocking,
            req.keyword,
            req.top_n,
            req.max_reviews,
            req.pages,
            req.enrich_details,
            on_progress,
        )
        _update_job(
            job_id,
            status=JobStatus.COMPLETED,
            message="SOURCING_COMPLETE",
            completed_at=datetime.now(timezone.utc).isoformat(),
            report=json.loads(report.model_dump_json()),
            json_path=str(json_path),
            md_path=str(md_path),
        )
    except Exception as exc:
        _update_job(
            job_id,
            status=JobStatus.FAILED,
            message="采集失败",
            completed_at=datetime.now(timezone.utc).isoformat(),
            error=format_exception(exc),
        )


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html_path = TEMPLATES_DIR / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=500, detail="index.html not found")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.post("/api/search", response_model=JobInfo)
async def start_search(req: SearchRequest, background_tasks: BackgroundTasks) -> JobInfo:
    job_id = str(uuid.uuid4())
    job = JobInfo(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="任务已创建，等待执行...",
        keyword=req.keyword,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _jobs[job_id] = job
    background_tasks.add_task(_execute_job, job_id, req)
    return job


@app.get("/api/jobs/{job_id}", response_model=JobInfo)
async def get_job(job_id: str) -> JobInfo:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job


@app.get("/api/reports")
async def list_reports() -> list[dict[str, str]]:
    out_dir = _output_dir()
    reports = []
    for path in sorted(out_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
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


@app.get("/api/reports/{filename}")
async def get_report(filename: str) -> dict[str, Any]:
    filename = _validate_report_filename(filename)
    path = _report_json_path(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="报告不存在")
    return json.loads(path.read_text(encoding="utf-8"))


@app.delete("/api/reports/{filename}")
async def delete_report(filename: str) -> dict[str, Any]:
    filename = _validate_report_filename(filename)
    json_path = _report_json_path(filename)
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="报告不存在")

    md_path = json_path.with_suffix(".md")
    deleted = [filename]
    json_path.unlink()

    if md_path.exists():
        md_path.unlink()
        deleted.append(md_path.name)

    return {"ok": True, "deleted": deleted}


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
