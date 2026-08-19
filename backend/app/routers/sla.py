from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.exceptions import NotFoundException
from app.models.user import User
from app.routers.tickets import check_ticket_access
from app.schemas.sla import SLAResponse
from app.services.sla_service import get_sla_record_by_ticket_id
from app.services.ticket_service import get_ticket_by_id

router = APIRouter()


@router.get("/tickets/{ticket_id}/sla", response_model=SLAResponse)
async def get_ticket_sla(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise NotFoundException("工单不存在")
    await check_ticket_access(db, ticket, current_user)

    sla = await get_sla_record_by_ticket_id(db, ticket_id)
    if not sla:
        raise NotFoundException("SLA 记录不存在")
    return sla


@router.get("/admin/sla/overdue", response_model=list[SLAResponse])
async def list_overdue_sla(
    breach_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    from sqlalchemy import select
    from app.models.sla_record import SLARecord

    stmt = select(SLARecord).where(
        (SLARecord.first_resp_breached.is_(True)) | (SLARecord.resolution_breached.is_(True))
    )
    if breach_type == "first_resp":
        stmt = stmt.where(SLARecord.first_resp_breached.is_(True))
    elif breach_type == "resolution":
        stmt = stmt.where(SLARecord.resolution_breached.is_(True))

    result = await db.execute(stmt.order_by(SLARecord.id.desc()))
    return result.scalars().all()
