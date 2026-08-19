import re
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import require_role
from app.schemas.report import (
    AgentPerformanceResponse,
    CategoryDistributionResponse,
    ExportRequest,
    OverviewResponse,
    SatisfactionResponse,
    TrendResponse,
)
from app.services.report_service import (
    get_agent_performance,
    get_category_distribution,
    get_overview,
    get_satisfaction_stats,
    get_trend,
    validate_date_range,
)
from app.tasks.export_tasks import generate_report_export

router = APIRouter()


@router.get("/admin/reports/overview", response_model=OverviewResponse)
async def overview(
    db=Depends(get_db),
    _=Depends(require_role("admin", "supervisor")),
):
    return await get_overview(db)


@router.get("/admin/reports/agent-performance", response_model=list[AgentPerformanceResponse])
async def agent_performance(
    start_date: date | None = None,
    end_date: date | None = None,
    db=Depends(get_db),
    _=Depends(require_role("admin", "supervisor")),
):
    return await get_agent_performance(db, start_date.isoformat() if start_date else None, end_date.isoformat() if end_date else None)


@router.get("/admin/reports/category-distribution", response_model=list[CategoryDistributionResponse])
async def category_distribution(
    start_date: date | None = None,
    end_date: date | None = None,
    db=Depends(get_db),
    _=Depends(require_role("admin", "supervisor")),
):
    return await get_category_distribution(db, start_date.isoformat() if start_date else None, end_date.isoformat() if end_date else None)


@router.get("/admin/reports/trend", response_model=list[TrendResponse])
async def trend(
    granularity: str = Query("day"),
    start_date: date | None = None,
    end_date: date | None = None,
    db=Depends(get_db),
    _=Depends(require_role("admin", "supervisor")),
):
    return await get_trend(
        db,
        granularity,
        start_date.isoformat() if start_date else None,
        end_date.isoformat() if end_date else None,
    )


@router.get("/admin/reports/satisfaction", response_model=SatisfactionResponse)
async def satisfaction(
    start_date: date | None = None,
    end_date: date | None = None,
    db=Depends(get_db),
    _=Depends(require_role("admin", "supervisor")),
):
    return await get_satisfaction_stats(db, start_date.isoformat() if start_date else None, end_date.isoformat() if end_date else None)


UUID_RE = re.compile(r"^[a-f0-9\-]{36}$")


@router.post("/admin/reports/export")
async def create_export(
    req: ExportRequest,
    _=Depends(require_role("admin", "supervisor")),
):
    if req.start_date and req.end_date:
        validate_date_range(req.start_date.isoformat(), req.end_date.isoformat())
    task_id = str(uuid.uuid4())
    generate_report_export.delay(
        task_id=task_id,
        report_type=req.report_type,
        format=req.format,
        start_date=req.start_date.isoformat() if req.start_date else None,
        end_date=req.end_date.isoformat() if req.end_date else None,
    )
    return {"task_id": task_id, "status": "pending"}


@router.get("/admin/reports/export/{task_id}")
async def get_export_status(
    task_id: str,
    _=Depends(require_role("admin", "supervisor")),
):
    if not UUID_RE.match(task_id):
        raise HTTPException(status_code=400, detail="无效的 task_id")

    settings = get_settings()
    export_dir = Path(settings.EXPORT_DIR)
    failed_marker = export_dir / f"{task_id}.failed"
    if failed_marker.exists():
        return {"task_id": task_id, "status": "failed", "download_url": None}
    for fmt in ("xlsx", "csv"):
        file_path = export_dir / f"{task_id}.{fmt}"
        if file_path.exists():
            return {
                "task_id": task_id,
                "status": "completed",
                "download_url": f"/api/v1/admin/reports/exports/download/{task_id}",
            }
    return {"task_id": task_id, "status": "pending", "download_url": None}


@router.get("/admin/reports/exports/download/{task_id}")
async def download_export(
    task_id: str,
    _=Depends(require_role("admin", "supervisor")),
):
    if not UUID_RE.match(task_id):
        raise HTTPException(status_code=400, detail="无效的 task_id")

    settings = get_settings()
    export_dir = Path(settings.EXPORT_DIR)
    for fmt in ("xlsx", "csv"):
        file_path = export_dir / f"{task_id}.{fmt}"
        if file_path.exists():
            media_type = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                if fmt == "xlsx"
                else "text/csv"
            )
            return FileResponse(
                path=str(file_path),
                filename=f"report_{task_id}.{fmt}",
                media_type=media_type,
            )
    raise HTTPException(status_code=404, detail="导出文件不存在或尚未完成")
