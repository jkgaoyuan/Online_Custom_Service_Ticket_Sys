from datetime import date, datetime, timedelta

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DuplicateException
from app.models.category import Category
from app.models.sla_record import SLARecord
from app.models.ticket import Ticket
from app.models.ticket_reply import TicketReply
from app.models.user import User


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


async def get_agent_performance(
    db: AsyncSession, start_date: str | None, end_date: str | None
) -> list[dict]:
    start, end = validate_date_range(start_date, end_date)

    # Assigned + resolved stats grouped by assignee
    assigned_result = await db.execute(
        select(
            Ticket.assignee_id,
            User.username,
            func.count(Ticket.id),
            func.sum(cast((Ticket.status == "resolved"), Integer)),
            func.avg(
                func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600
            ),
        )
        .join(User, Ticket.assignee_id == User.id)
        .where(
            Ticket.created_at >= start,
            Ticket.created_at <= end,
            Ticket.assignee_id.isnot(None),
        )
        .group_by(Ticket.assignee_id, User.username)
    )

    assigned_rows = {row[0]: row for row in assigned_result.all()}

    # First response stats: earliest non-internal reply per ticket
    earliest_reply_subq = (
        select(
            TicketReply.ticket_id,
            func.min(TicketReply.created_at).label("first_reply_at"),
        )
        .where(TicketReply.is_internal.is_(False))
        .group_by(TicketReply.ticket_id)
        .subquery()
    )

    first_reply_result = await db.execute(
        select(
            TicketReply.author_id,
            func.avg(
                func.extract("epoch", TicketReply.created_at - Ticket.created_at) / 3600
            ),
        )
        .join(
            earliest_reply_subq,
            (TicketReply.ticket_id == earliest_reply_subq.c.ticket_id)
            & (TicketReply.created_at == earliest_reply_subq.c.first_reply_at),
        )
        .join(Ticket, TicketReply.ticket_id == Ticket.id)
        .where(
            Ticket.created_at >= start,
            Ticket.created_at <= end,
        )
        .group_by(TicketReply.author_id)
    )

    first_reply_map = {row[0]: row[1] for row in first_reply_result.all()}

    result = []
    for agent_id, row in assigned_rows.items():
        avg_resolution = row[4] if row[4] is not None else 0.0
        avg_first_resp = first_reply_map.get(agent_id, 0.0)
        if avg_first_resp is None:
            avg_first_resp = 0.0
        result.append({
            "agent_id": agent_id,
            "agent_name": row[1],
            "total_assigned": row[2],
            "resolved_count": row[3] or 0,
            "avg_first_resp_hours": round(avg_first_resp, 2),
            "avg_resolution_hours": round(avg_resolution, 2),
        })

    return sorted(result, key=lambda x: x["total_assigned"], reverse=True)
