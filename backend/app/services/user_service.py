import random
import string
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DuplicateException, NotFoundException, PermissionDeniedException
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.user import UserUpdate
from app.services.notification_service import create_notification
from app.utils.security import get_password_hash


async def list_users(
    db: AsyncSession,
    role: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    result = await db.execute(
        stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()

    # Batch count tickets per assignee
    user_ids = [u.id for u in users]
    ticket_counts = {}
    if user_ids:
        count_result = await db.execute(
            select(Ticket.assignee_id, func.count(Ticket.id))
            .where(Ticket.assignee_id.in_(user_ids))
            .group_by(Ticket.assignee_id)
        )
        ticket_counts = {uid: cnt for uid, cnt in count_result.all()}

    items = []
    for user in users:
        items.append(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "ticket_count": ticket_counts.get(user.id, 0),
            }
        )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def update_user(db: AsyncSession, user_id: int, update_data: UserUpdate) -> User:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise NotFoundException("用户不存在")

    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        return user

    # Check username uniqueness excluding self
    if "username" in update_dict and update_dict["username"] != user.username:
        existing = await db.execute(
            select(User).where(User.username == update_dict["username"], User.id != user_id)
        )
        if existing.scalar_one_or_none():
            raise DuplicateException("用户名已存在")

    # Check email uniqueness excluding self
    if "email" in update_dict and update_dict["email"] != user.email:
        existing = await db.execute(
            select(User).where(User.email == update_dict["email"], User.id != user_id)
        )
        if existing.scalar_one_or_none():
            raise DuplicateException("邮箱已存在")

    for key, value in update_dict.items():
        setattr(user, key, value)

    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


async def reset_user_password(db: AsyncSession, user_id: int) -> str:
    user = await get_user_by_id(db, user_id)
    if not user:
        raise NotFoundException("用户不存在")

    temp_password = "".join(random.choices(string.ascii_letters + string.digits, k=12))
    user.password_hash = get_password_hash(temp_password)
    user.updated_at = datetime.utcnow()

    await create_notification(
        db=db,
        user_id=user.id,
        type="password_reset",
        title="密码已重置",
        message=f"您的密码已被管理员重置，请使用临时密码登录并及时修改。",
        data={"temp_password": temp_password},
    )

    await db.commit()
    return temp_password


async def get_user_stats(db: AsyncSession, user_id: int) -> dict | None:
    total_result = await db.execute(
        select(func.count()).where(Ticket.assignee_id == user_id)
    )
    total_tickets = total_result.scalar_one()

    if total_tickets == 0:
        return None

    resolved_result = await db.execute(
        select(func.count()).where(Ticket.assignee_id == user_id, Ticket.status == "resolved")
    )
    resolved_tickets = resolved_result.scalar_one()

    open_result = await db.execute(
        select(func.count()).where(Ticket.assignee_id == user_id, Ticket.status == "open")
    )
    open_tickets = open_result.scalar_one()

    return {
        "total_tickets": total_tickets,
        "resolved_tickets": resolved_tickets,
        "open_tickets": open_tickets,
        "avg_first_resp_minutes": None,
    }
