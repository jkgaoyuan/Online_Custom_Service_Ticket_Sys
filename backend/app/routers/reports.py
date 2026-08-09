from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.exceptions import TicketSystemException
from app.schemas.report import (
    AgentPerformanceResponse,
    CategoryDistributionResponse,
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
)

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
