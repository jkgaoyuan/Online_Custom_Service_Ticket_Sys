import csv
import uuid
from pathlib import Path

import pandas as pd
from celery import shared_task

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.services.report_service import (
    get_agent_performance,
    get_category_distribution,
    get_overview,
    get_satisfaction_stats,
    get_trend,
)

REPORT_TYPE_TO_FUNC = {
    "overview": get_overview,
    "agent_performance": get_agent_performance,
    "category_distribution": get_category_distribution,
    "trend": get_trend,
    "satisfaction": get_satisfaction_stats,
}


def _sanitize_for_export(value):
    """Prevent CSV/Excel formula injection."""
    if not isinstance(value, str):
        return value
    if value and value[0] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def _sanitize_rows(rows):
    if isinstance(rows, dict):
        return {k: _sanitize_for_export(v) for k, v in rows.items()}
    if isinstance(rows, list):
        return [_sanitize_rows(row) for row in rows]
    return rows


@shared_task(name="tasks.generate_report_export")
def generate_report_export(task_id: str, report_type: str, format: str, start_date: str | None, end_date: str | None):
    import asyncio
    asyncio.run(_async_generate_report_export(task_id, report_type, format, start_date, end_date))


async def _async_generate_report_export(task_id, report_type, format, start_date, end_date):
    settings = get_settings()
    export_dir = Path(settings.EXPORT_DIR)
    export_dir.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as db:
        func = REPORT_TYPE_TO_FUNC.get(report_type)
        if func is None:
            raise ValueError(f"Unknown report_type: {report_type}")

        if report_type == "overview":
            data = await func(db)
        elif report_type == "trend":
            # Default granularity for export is day
            data = await func(db, "day", start_date, end_date)
        else:
            data = await func(db, start_date, end_date)

    if report_type == "overview" or report_type == "satisfaction":
        # Single dict -> list of one
        rows = [data]
    else:
        rows = data if isinstance(data, list) else [data]

    rows = _sanitize_rows(rows)
    df = pd.DataFrame(rows)

    file_path = export_dir / f"{task_id}.{format}"
    if format == "xlsx":
        df.to_excel(file_path, index=False, engine="openpyxl")
    else:
        df.to_csv(file_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
