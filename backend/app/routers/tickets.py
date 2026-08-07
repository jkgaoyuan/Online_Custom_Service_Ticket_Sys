from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import NotFoundException
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketResponse, TicketUpdate
from app.services.ticket_service import (
    create_ticket,
    get_ticket_by_id,
    get_tickets_query,
    update_ticket,
)

router = APIRouter()


@router.post(
    "/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED
)
async def create_ticket_endpoint(
    data: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await create_ticket(db, data, current_user.id)
    return ticket


@router.get("/tickets", response_model=dict)
async def list_tickets(
    status: str | None = None,
    priority: str | None = None,
    category_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await get_tickets_query(
        db, current_user, status, priority, category_id, page, page_size
    )
    # Serialize items to ensure JSON compatibility
    return {
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "items": [
            TicketResponse.model_validate(ticket).model_dump()
            for ticket in result["items"]
        ],
    }


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise NotFoundException("工单不存在")
    # TODO: data scope check in Task 3
    return ticket
