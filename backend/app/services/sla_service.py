from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.sla_record import SLARecord
from app.models.ticket import Ticket

DEFAULT_SLA = {
    "P0": {"first_resp_hours": 1, "resolution_hours": 4},
    "P1": {"first_resp_hours": 4, "resolution_hours": 24},
    "P2": {"first_resp_hours": 8, "resolution_hours": 48},
    "P3": {"first_resp_hours": 24, "resolution_hours": 72},
}


def _resolve_sla_config(category_sla_config: dict, priority: str) -> dict:
    """从 category.sla_config 解析出指定优先级的 SLA 配置。兼容旧版 flat 格式。"""
    sla_config = category_sla_config or {}
    if "first_resp_hours" in sla_config and "P0" not in sla_config:
        return {
            "first_resp_hours": sla_config["first_resp_hours"],
            "resolution_hours": sla_config["resolution_hours"],
        }
    return sla_config.get(priority, DEFAULT_SLA[priority])


async def create_sla_record(db: AsyncSession, ticket: Ticket) -> SLARecord:
    """在 create_ticket 内部调用，ticket 已 flush 有 id。不自行 commit。"""
    cat_result = await db.execute(select(Category).where(Category.id == ticket.category_id))
    category = cat_result.scalar_one()

    priority_config = _resolve_sla_config(category.sla_config, ticket.priority)
    now = datetime.utcnow()

    record = SLARecord(
        ticket_id=ticket.id,
        priority=ticket.priority,
        first_resp_hours=priority_config["first_resp_hours"],
        resolution_hours=priority_config["resolution_hours"],
        first_resp_due=now + timedelta(hours=priority_config["first_resp_hours"]),
        resolution_due=now + timedelta(hours=priority_config["resolution_hours"]),
    )
    db.add(record)
    return record


async def get_sla_record_by_ticket_id(db: AsyncSession, ticket_id: int) -> SLARecord | None:
    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket_id))
    return result.scalar_one_or_none()
