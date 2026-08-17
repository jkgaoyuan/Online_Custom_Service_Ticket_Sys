from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.ticket import Ticket
from app.models.ticket_reply import TicketReply
from app.models.user import User
from app.schemas.user import (
    UserDetailResponse,
    UserListResponse,
    UserPasswordResetResponse,
    UserResponse,
    UserStats,
    UserUpdate,
)
from app.services.user_service import (
    get_user_by_id,
    list_users,
    reset_user_password,
    update_user,
)

router = APIRouter()


async def _get_user_stats(db: AsyncSession, user_id: int) -> UserStats:
    """Inline agent stats because report_service.get_agent_stats does not exist."""
    total_result = await db.execute(
        select(func.count(Ticket.id)).where(Ticket.assignee_id == user_id)
    )
    total_tickets = total_result.scalar() or 0

    resolved_result = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.assignee_id == user_id, Ticket.status == "resolved"
        )
    )
    resolved_tickets = resolved_result.scalar() or 0

    open_result = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.assignee_id == user_id, Ticket.status == "open"
        )
    )
    open_tickets = open_result.scalar() or 0

    earliest_reply_subq = (
        select(
            TicketReply.ticket_id,
            func.min(TicketReply.created_at).label("first_reply_at"),
        )
        .where(TicketReply.is_internal.is_(False))
        .group_by(TicketReply.ticket_id)
        .subquery()
    )

    avg_first_resp_result = await db.execute(
        select(
            func.avg(
                func.extract(
                    "epoch", earliest_reply_subq.c.first_reply_at - Ticket.created_at
                )
            )
            / 60
        )
        .join(
            earliest_reply_subq,
            earliest_reply_subq.c.ticket_id == Ticket.id,
        )
        .where(Ticket.assignee_id == user_id)
    )
    avg_first_resp_minutes = avg_first_resp_result.scalar()
    if avg_first_resp_minutes is None:
        avg_first_resp_minutes = 0.0

    return UserStats(
        total_tickets=total_tickets,
        resolved_tickets=resolved_tickets,
        open_tickets=open_tickets,
        avg_first_resp_minutes=round(avg_first_resp_minutes, 2),
    )


@router.get("/admin/users", response_model=UserListResponse)
async def list_users_endpoint(
    role: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    if current_user.role == "supervisor" and role is None:
        role = "agent"
    if current_user.role == "supervisor" and role and role != "agent":
        raise HTTPException(status_code=403, detail="无权查看该角色用户")

    return await list_users(
        db, role=role, is_active=is_active, page=page, page_size=page_size
    )


@router.get("/admin/users/{user_id}", response_model=UserDetailResponse)
async def get_user_detail(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if current_user.role == "supervisor" and user.role != "agent":
        raise HTTPException(status_code=403, detail="无权查看该用户")

    stats = None
    if user.role in ("agent", "supervisor", "admin"):
        stats = await _get_user_stats(db, user_id)

    return UserDetailResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        stats=stats,
    )


@router.put("/admin/users/{user_id}", response_model=UserResponse)
async def update_user_endpoint(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if current_user.role == "supervisor":
        if user.role != "agent":
            raise HTTPException(status_code=403, detail="无权修改该用户")
        if data.role and data.role != "agent":
            raise HTTPException(status_code=403, detail="只能设置角色为 agent")

    if current_user.id == user_id and data.role and data.role != user.role:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")

    updated = await update_user(db, user_id, data.model_dump(exclude_unset=True))
    return UserResponse.model_validate(updated)


@router.post("/admin/users/{user_id}/reset-password", response_model=UserPasswordResetResponse)
async def reset_password_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    temp_password = await reset_user_password(db, user_id)
    return UserPasswordResetResponse(temp_password=temp_password)
