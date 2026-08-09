from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DuplicateException
from app.models.category import Category
from app.models.sla_record import SLARecord
from app.models.ticket import Ticket


MAX_DATE_RANGE_DAYS = 365


def validate_date_range(start_date: str | None, end_date: str | None) -> tuple[datetime, datetime]:
    now = datetime.utcnow()
    if start_date and end_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1, microseconds=-1)
        if (end - start).days > MAX_DATE_RANGE_DAYS:
            raise DuplicateException(f"日期范围不能超过 {MAX_DATE_RANGE_DAYS} 天")
        if start > end:
            raise DuplicateException("开始日期不能晚于结束日期")
        return start, end
    end = now
    start = now - timedelta(days=30)
    return start, end


async def get_overview(db: AsyncSession) -> dict:
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    total_result = await db.execute(select(func.count(Ticket.id)))
    total = total_result.scalar() or 0

    today_result = await db.execute(
        select(func.count(Ticket.id)).where(Ticket.created_at >= today_start)
    )
    today_new = today_result.scalar() or 0

    week_result = await db.execute(
        select(func.count(Ticket.id)).where(Ticket.created_at >= week_start)
    )
    week_new = week_result.scalar() or 0

    month_result = await db.execute(
        select(func.count(Ticket.id)).where(Ticket.created_at >= month_start)
    )
    month_new = month_result.scalar() or 0

    status_result = await db.execute(
        select(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status)
    )
    status_distribution = {row[0]: row[1] for row in status_result.all()}

    sla_result = await db.execute(
        select(func.count(SLARecord.id)).where(
            SLARecord.first_resp_breached.is_(False),
            SLARecord.resolution_breached.is_(False),
        )
    )
    sla_ok = sla_result.scalar() or 0
    sla_total_result = await db.execute(select(func.count(SLARecord.id)))
    sla_total = sla_total_result.scalar() or 0
    sla_compliance_rate = (sla_ok / sla_total) if sla_total > 0 else 1.0

    sat_result = await db.execute(
        select(func.count(Ticket.id)).where(Ticket.satisfaction.isnot(None))
    )
    sat_count = sat_result.scalar() or 0

    sat_scores = {"satisfied": 5, "neutral": 3, "dissatisfied": 1}
    score_sum = 0
    sat_details = await db.execute(
        select(Ticket.satisfaction, func.count(Ticket.id))
        .where(Ticket.satisfaction.isnot(None))
        .group_by(Ticket.satisfaction)
    )
    sat_distribution = {}
    for row in sat_details.all():
        sat_distribution[row[0]] = row[1]
        score_sum += sat_scores.get(row[0], 0) * row[1]

    avg_satisfaction = (score_sum / sat_count) if sat_count > 0 else 0.0

    return {
        "total_tickets": total,
        "today_new": today_new,
        "week_new": week_new,
        "month_new": month_new,
        "status_distribution": status_distribution,
        "sla_compliance_rate": round(sla_compliance_rate, 2),
        "avg_satisfaction": round(avg_satisfaction, 2),
    }


async def get_category_distribution(
    db: AsyncSession, start_date: str | None, end_date: str | None
) -> list[dict]:
    start, end = validate_date_range(start_date, end_date)

    total_result = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.created_at >= start, Ticket.created_at <= end
        )
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        select(Category.id, Category.name, func.count(Ticket.id))
        .join(Ticket, Ticket.category_id == Category.id)
        .where(Ticket.created_at >= start, Ticket.created_at <= end)
        .group_by(Category.id, Category.name)
        .order_by(func.count(Ticket.id).desc())
    )

    rows = result.all()
    return [
        {
            "category_id": row[0],
            "category_name": row[1],
            "count": row[2],
            "percentage": round(row[2] / total, 3) if total > 0 else 0.0,
        }
        for row in rows
    ]


async def get_satisfaction_stats(
    db: AsyncSession, start_date: str | None, end_date: str | None
) -> dict:
    start, end = validate_date_range(start_date, end_date)

    total_closed_result = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.closed_at.isnot(None),
            Ticket.created_at >= start,
            Ticket.created_at <= end,
        )
    )
    total_in_range = total_closed_result.scalar() or 0

    sat_details = await db.execute(
        select(Ticket.satisfaction, func.count(Ticket.id))
        .where(
            Ticket.satisfaction.isnot(None),
            Ticket.closed_at.isnot(None),
            Ticket.created_at >= start,
            Ticket.created_at <= end,
        )
        .group_by(Ticket.satisfaction)
    )

    distribution = {}
    score_sum = 0
    total_rated = 0
    scores = {"satisfied": 5, "neutral": 3, "dissatisfied": 1}
    for row in sat_details.all():
        distribution[row[0]] = row[1]
        total_rated += row[1]
        score_sum += scores.get(row[0], 0) * row[1]

    avg_score = (score_sum / total_rated) if total_rated > 0 else 0.0
    participation_rate = (total_rated / total_in_range) if total_in_range > 0 else 0.0

    return {
        "distribution": distribution,
        "avg_score": round(avg_score, 2),
        "participation_rate": round(participation_rate, 2),
        "total_rated": total_rated,
        "total_in_range": total_in_range,
    }
