from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.ticket_reply import TicketReply
from app.schemas.ticket_reply import ReplyCreate
from app.models.ticket import Ticket

async def create_reply(db: AsyncSession, ticket: Ticket, data: ReplyCreate, author_id: int) -> TicketReply:
    reply = TicketReply(ticket_id=ticket.id, author_id=author_id, content=data.content, is_internal=data.is_internal)
    db.add(reply)
    await db.commit()
    await db.refresh(reply)
    return reply

async def get_replies_by_ticket(db: AsyncSession, ticket_id: int, include_internal: bool = False) -> list[TicketReply]:
    query = select(TicketReply).where(TicketReply.ticket_id == ticket_id).order_by(TicketReply.created_at.asc())
    if not include_internal:
        query = query.where(TicketReply.is_internal == False)
    result = await db.execute(query)
    return result.scalars().all()
