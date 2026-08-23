from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.sse import send_event
from app.models.ticket_reply import TicketReply
from app.schemas.ticket_reply import ReplyCreate
from app.models.ticket import Ticket
from app.services.sla_service import get_sla_record_by_ticket_id

async def create_reply(db: AsyncSession, ticket: Ticket, data: ReplyCreate, author_id: int, is_agent_reply: bool = False) -> TicketReply:
    reply = TicketReply(ticket_id=ticket.id, author_id=author_id, content=data.content, is_internal=data.is_internal)
    db.add(reply)
    await db.commit()
    await db.refresh(reply)

    if is_agent_reply:
        sla = await get_sla_record_by_ticket_id(db, ticket.id)
        if sla and sla.first_resp_at is None:
            sla.first_resp_at = datetime.utcnow()
            await db.commit()

        if not data.is_internal:
            await send_event(
                ticket.requester_id,
                "new_notification",
                {
                    "id": None,
                    "type": "ticket_replied",
                    "title": f"工单 #{ticket.ticket_no} 有新回复",
                    "message": "客服已回复您的工单",
                    "ticket_id": ticket.id,
                    "ticket_no": ticket.ticket_no,
                },
            )
    else:
        # Customer reply
        if ticket.assignee_id is not None:
            await send_event(
                ticket.assignee_id,
                "new_notification",
                {
                    "id": None,
                    "type": "ticket_replied",
                    "title": f"工单 #{ticket.ticket_no} 有新回复",
                    "message": "客户已回复工单",
                    "ticket_id": ticket.id,
                    "ticket_no": ticket.ticket_no,
                },
            )

    # Re-query to eagerly load author relationship for serialization
    result = await db.execute(
        select(TicketReply)
        .where(TicketReply.id == reply.id)
        .options(selectinload(TicketReply.author))
    )
    return result.scalar_one()

async def get_replies_by_ticket(db: AsyncSession, ticket_id: int, include_internal: bool = False) -> list[TicketReply]:
    query = (
        select(TicketReply)
        .where(TicketReply.ticket_id == ticket_id)
        .order_by(TicketReply.created_at.asc())
        .options(selectinload(TicketReply.author))
    )
    if not include_internal:
        query = query.where(TicketReply.is_internal == False)
    result = await db.execute(query)
    return result.scalars().all()
