from datetime import datetime

from sqlalchemy import func, or_, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.sse import send_event
from app.exceptions import DuplicateException, TicketSystemException
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.services.sla_service import create_sla_record, get_sla_record_by_ticket_id
from app.services.notification_service import create_notification


async def generate_ticket_no(db: AsyncSession) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"TK-{today}-"
    result = await db.execute(
        select(func.count(Ticket.id)).where(Ticket.ticket_no.like(f"{prefix}%"))
    )
    count = result.scalar() + 1
    return f"{prefix}{count:04d}"


async def create_ticket(
    db: AsyncSession, data: TicketCreate, requester_id: int
) -> Ticket:
    ticket_no = await generate_ticket_no(db)
    ticket = Ticket(
        ticket_no=ticket_no,
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        priority=data.priority,
        requester_id=requester_id,
        assignee_id=data.assignee_id,
        source=data.source,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    # 创建 SLA 记录（ticket 已有 id）
    await create_sla_record(db, ticket)
    await db.commit()
    await db.refresh(ticket)

    if ticket.assignee_id is not None:
        await send_event(
            ticket.assignee_id,
            "new_notification",
            {
                "id": None,
                "type": "ticket_assigned",
                "title": f"新工单分配：{ticket.title}",
                "message": f"工单 #{ticket.ticket_no} 已分配给您",
                "ticket_id": ticket.id,
                "ticket_no": ticket.ticket_no,
            },
        )

    return ticket


async def get_ticket_by_id(db: AsyncSession, ticket_id: int) -> Ticket | None:
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    return result.scalar_one_or_none()


async def update_ticket(
    db: AsyncSession, ticket: Ticket, data: TicketUpdate
) -> Ticket:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def get_tickets_query(
    db: AsyncSession,
    current_user: User,
    status: str | None = None,
    priority: str | None = None,
    category_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
):
    query = select(Ticket)
    if current_user.role == "customer":
        query = query.where(Ticket.requester_id == current_user.id)
    elif current_user.role == "agent":
        query = query.where(
            or_(
                Ticket.assignee_id == current_user.id,
                Ticket.status == "open",
                and_(Ticket.assignee_id.is_(None), Ticket.status.in_(["open", "in_progress"])),
            )
        )

    if status:
        query = query.where(Ticket.status == status)
    if priority:
        query = query.where(Ticket.priority == priority)
    if category_id:
        query = query.where(Ticket.category_id == category_id)

    total_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = total_result.scalar()

    query = (
        query.order_by(Ticket.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    query = query.options(selectinload(Ticket.requester))
    result = await db.execute(query)
    items = result.scalars().all()
    return {"total": total, "page": page, "page_size": page_size, "items": items}


VALID_TRANSITIONS = {
    "open": {"in_progress", "closed"},
    "in_progress": {"waiting", "resolved", "open"},
    "waiting": {"in_progress", "resolved"},
    "resolved": {"closed", "in_progress"},
    "closed": set(),
}


def can_transition(current: str, target: str) -> bool:
    return target in VALID_TRANSITIONS.get(current, set())


async def transition_ticket_status(db: AsyncSession, ticket: Ticket, target_status: str) -> Ticket:
    if not can_transition(ticket.status, target_status):
        raise DuplicateException(f"无法从 {ticket.status} 流转到 {target_status}")

    # 禁止将无负责人的工单流转到需要负责人的终态
    if target_status in ("resolved", "waiting") and ticket.assignee_id is None:
        raise TicketSystemException("该工单未分配负责人，请先分派或接单")

    old_status = ticket.status
    ticket.status = target_status

    if target_status == "resolved":
        ticket.resolved_at = datetime.utcnow()
        sla = await get_sla_record_by_ticket_id(db, ticket.id)
        if sla and sla.resolved_at is None:
            sla.resolved_at = datetime.utcnow()

    if target_status == "closed":
        ticket.closed_at = datetime.utcnow()
        await create_notification(
            db,
            user_id=ticket.requester_id,
            type="satisfaction_invite",
            title=f"工单 #{ticket.ticket_no} 已关闭，请评价我们的服务",
            message="您的工单已处理完毕，点击评价本次服务体验。",
            data={"ticket_id": ticket.id, "ticket_no": ticket.ticket_no},
        )
        await send_event(
            ticket.requester_id,
            "new_notification",
            {
                "id": None,
                "type": "satisfaction_invite",
                "title": f"工单 #{ticket.ticket_no} 已关闭，请评价我们的服务",
                "message": "您的工单已处理完毕，点击评价本次服务体验。",
                "ticket_id": ticket.id,
                "ticket_no": ticket.ticket_no,
            },
        )

    # 重新打开：清空 resolved_at，让其继续受 resolution SLA 约束
    if old_status == "resolved" and target_status == "in_progress":
        ticket.resolved_at = None
        sla = await get_sla_record_by_ticket_id(db, ticket.id)
        if sla:
            sla.resolved_at = None

    await db.commit()
    await db.refresh(ticket)
    return ticket


async def submit_satisfaction(
    db: AsyncSession, ticket: Ticket, user_id: int, rating: str, note: str | None
) -> Ticket:
    if ticket.requester_id != user_id:
        raise TicketSystemException("只能评价自己的工单", status_code=403)

    if ticket.status != "closed":
        raise TicketSystemException("工单未关闭，无法评价", status_code=400)

    if ticket.satisfaction_at is not None:
        raise TicketSystemException("该工单已评价，不可修改", status_code=400)

    ticket.satisfaction = rating
    ticket.satisfaction_note = note[:500] if note else None
    ticket.satisfaction_at = datetime.utcnow()
    await db.commit()
    await db.refresh(ticket)
    return ticket
