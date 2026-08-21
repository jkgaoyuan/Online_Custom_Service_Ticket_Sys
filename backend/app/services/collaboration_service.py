from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.sse import send_event
from app.exceptions import NotFoundException, TicketSystemException, ValidationException
from app.models.collaboration import TicketCollaboration
from app.models.ticket import Ticket
from app.models.user import User
from app.services.notification_service import create_notification


def _truncate_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    return reason[:500]


async def transfer_ticket(
    db: AsyncSession,
    ticket_id: int,
    from_user_id: int,
    to_user_id: int,
    reason: str | None,
) -> Ticket:
    # Validate ticket exists
    ticket_result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = ticket_result.scalar_one_or_none()
    if ticket is None:
        raise NotFoundException("工单不存在")

    # Only current assignee can transfer (supervisor/admin bypass)
    from_user_result = await db.execute(select(User).where(User.id == from_user_id))
    from_user = from_user_result.scalar_one()
    if from_user.role not in ("supervisor", "admin") and ticket.assignee_id != from_user_id:
        raise ValidationException("只有当前处理人才能执行此操作")

    # Cannot transfer to self
    if from_user_id == to_user_id:
        raise ValidationException("不能转交/协助给自己")

    # Validate target is active agent
    user_result = await db.execute(select(User).where(User.id == to_user_id))
    target_user = user_result.scalar_one_or_none()
    if target_user is None or target_user.role != "agent" or not target_user.is_active:
        raise ValidationException("转交目标必须是有效的客服角色")

    # Cannot transfer to self (same assignee)
    if ticket.assignee_id == to_user_id:
        raise ValidationException("不能转交给当前处理人")

    # Create transfer record
    collaboration = TicketCollaboration(
        ticket_id=ticket_id,
        type="transfer",
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        reason=_truncate_reason(reason),
    )
    db.add(collaboration)

    # Update ticket assignee and status
    old_assignee_id = ticket.assignee_id
    ticket.assignee_id = to_user_id
    if ticket.status == "open":
        ticket.status = "in_progress"

    # Notify new assignee
    source_text = "系统" if old_assignee_id is None else "客服"
    await create_notification(
        db,
        user_id=to_user_id,
        type="ticket_transferred",
        title=f"工单 #{ticket.ticket_no} 已转交给您",
        message=f"来自 {source_text} 的转交，原因：{reason or '无'}"[:200],
        data={"ticket_id": ticket.id, "ticket_no": ticket.ticket_no},
    )
    await send_event(
        to_user_id,
        "new_notification",
        {
            "id": None,
            "type": "ticket_transferred",
            "title": f"工单 #{ticket.ticket_no} 已转交给您",
            "message": f"来自 {source_text} 的转交，原因：{reason or '无'}"[:200],
            "ticket_id": ticket.id,
            "ticket_no": ticket.ticket_no,
        },
    )

    await db.commit()
    await db.refresh(ticket)
    await db.refresh(collaboration)
    return ticket


async def request_assistance(
    db: AsyncSession,
    ticket_id: int,
    from_user_id: int,
    to_user_id: int,
    reason: str | None,
) -> TicketCollaboration:
    # Validate ticket exists
    ticket_result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = ticket_result.scalar_one_or_none()
    if ticket is None:
        raise NotFoundException("工单不存在")

    # Only current assignee can request assistance (supervisor/admin bypass)
    from_user_result = await db.execute(select(User).where(User.id == from_user_id))
    from_user = from_user_result.scalar_one()
    if from_user.role not in ("supervisor", "admin") and ticket.assignee_id != from_user_id:
        raise ValidationException("只有当前处理人才能执行此操作")

    # Cannot assist self
    if from_user_id == to_user_id:
        raise ValidationException("不能转交/协助给自己")

    # Validate target is active agent
    user_result = await db.execute(select(User).where(User.id == to_user_id))
    target_user = user_result.scalar_one_or_none()
    if target_user is None or target_user.role != "agent" or not target_user.is_active:
        raise ValidationException("协助目标必须是有效的客服角色")

    # Check duplicate assist for same ticket + same agent
    existing_result = await db.execute(
        select(TicketCollaboration).where(
            TicketCollaboration.ticket_id == ticket_id,
            TicketCollaboration.to_user_id == to_user_id,
            TicketCollaboration.type == "assist",
        )
    )
    if existing_result.scalar_one_or_none() is not None:
        raise ValidationException("该客服已对此工单提供协助，不可重复请求")

    # Create assist record
    collaboration = TicketCollaboration(
        ticket_id=ticket_id,
        type="assist",
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        reason=_truncate_reason(reason),
    )
    db.add(collaboration)

    # Notify assist agent
    await create_notification(
        db,
        user_id=to_user_id,
        type="assistance_requested",
        title=f"工单 #{ticket.ticket_no} 请求协助",
        message=f"协助说明：{reason or '无'}"[:200],
        data={"ticket_id": ticket.id, "ticket_no": ticket.ticket_no},
    )
    await send_event(
        to_user_id,
        "new_notification",
        {
            "id": None,
            "type": "assistance_requested",
            "title": f"工单 #{ticket.ticket_no} 请求协助",
            "message": f"协助说明：{reason or '无'}"[:200],
            "ticket_id": ticket.id,
            "ticket_no": ticket.ticket_no,
        },
    )

    await db.commit()
    await db.refresh(collaboration)
    # Eagerly load user relationships for response serialization
    result = await db.execute(
        select(TicketCollaboration)
        .where(TicketCollaboration.id == collaboration.id)
        .options(selectinload(TicketCollaboration.from_user), selectinload(TicketCollaboration.to_user))
    )
    return result.scalar_one()


async def get_collaborations(db: AsyncSession, ticket_id: int) -> list[TicketCollaboration]:
    result = await db.execute(
        select(TicketCollaboration)
        .where(TicketCollaboration.ticket_id == ticket_id)
        .options(selectinload(TicketCollaboration.from_user), selectinload(TicketCollaboration.to_user))
        .order_by(TicketCollaboration.created_at.desc())
    )
    return result.scalars().all()
