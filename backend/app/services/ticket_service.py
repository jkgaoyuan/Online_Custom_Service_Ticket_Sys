from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketUpdate


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
            or_(Ticket.assignee_id == current_user.id, Ticket.status == "open")
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
    result = await db.execute(query)
    items = result.scalars().all()
    return {"total": total, "page": page, "page_size": page_size, "items": items}
