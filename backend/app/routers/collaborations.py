from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.exceptions import (
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
)
from app.models.collaboration import TicketCollaboration
from app.models.user import User
from app.routers.tickets import check_ticket_access
from app.schemas.collaboration import CollaborationCreate, CollaborationResponse
from app.schemas.ticket import TicketResponse
from app.services.collaboration_service import (
    get_collaborations,
    request_assistance,
    transfer_ticket,
)
from app.services.ticket_service import get_ticket_by_id

router = APIRouter()


@router.post(
    "/tickets/{ticket_id}/transfer",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
async def transfer_ticket_endpoint(
    ticket_id: int,
    data: CollaborationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "supervisor", "admin")),
):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise NotFoundException("工单不存在")
    await check_ticket_access(db, ticket, current_user)
    ticket = await transfer_ticket(
        db, ticket_id, current_user.id, data.to_user_id, data.reason
    )
    return TicketResponse.model_validate(ticket)


@router.post(
    "/tickets/{ticket_id}/assist",
    response_model=CollaborationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_assistance_endpoint(
    ticket_id: int,
    data: CollaborationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "supervisor", "admin")),
):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise NotFoundException("工单不存在")
    await check_ticket_access(db, ticket, current_user)
    collab = await request_assistance(
        db, ticket_id, current_user.id, data.to_user_id, data.reason
    )
    # Eager load relationships for response serialization
    result = await db.execute(
        select(TicketCollaboration)
        .where(TicketCollaboration.id == collab.id)
        .options(selectinload(TicketCollaboration.from_user), selectinload(TicketCollaboration.to_user))
    )
    collab = result.scalar_one()
    return CollaborationResponse.model_validate(collab)


@router.get(
    "/tickets/{ticket_id}/collaborations",
    response_model=list[CollaborationResponse],
)
async def list_collaborations(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "supervisor", "admin")),
):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise NotFoundException("工单不存在")
    await check_ticket_access(db, ticket, current_user)
    return await get_collaborations(db, ticket_id)
