import secrets
import string
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket
from app.models.user import User
from app.services.notification_service import create_notification
from app.utils.security import get_password_hash


async def list_users(
    db: AsyncSession,
    role: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    base_stmt = select(User)
    count_stmt = select(func.count(User.id))

    filters = []
    if role:
        filters.append(User.role == role)
    if is_active is not None:
        filters.append(User.is_active == is_active)

    if filters:
        base_stmt = base_stmt.where(and_(*filters))
        count_stmt = count_stmt.where(and_(*filters))

    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    result = await db.execute(
        base_stmt
        .order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    users = result.scalars().all()

    # 批量统计工单数
    user_ids = [u.id for u in users]
    stats_stmt = (
        select(Ticket.assignee_id, func.count(Ticket.id))
        .where(Ticket.assignee_id.in_(user_ids))
        .group_by(Ticket.assignee_id)
    )
    stats_result = await db.execute(stats_stmt)
    ticket_counts = {uid: cnt for uid, cnt in stats_result.all()}

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "max_concurrent_tickets": u.max_concurrent_tickets,
                "created_at": u.created_at,
                "ticket_count": ticket_counts.get(u.id, 0),
            }
            for u in users
        ],
    }


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def update_user(db: AsyncSession, user_id: int, update_data: dict) -> User:
    result = await db.execute(
        select(User).where(User.id == user_id).with_for_update()
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if "username" in update_data and update_data["username"] != user.username:
        dup = await db.execute(
            select(User)
            .where(User.username == update_data["username"], User.id != user_id)
            .with_for_update()
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="用户名已存在")
        user.username = update_data["username"]

    if "email" in update_data and update_data["email"] != user.email:
        dup = await db.execute(
            select(User)
            .where(User.email == update_data["email"], User.id != user_id)
            .with_for_update()
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="邮箱已存在")
        user.email = update_data["email"]

    if "role" in update_data:
        if update_data["role"] not in ("customer", "agent", "supervisor", "admin"):
            raise HTTPException(status_code=400, detail="无效的角色")
        user.role = update_data["role"]

    if "is_active" in update_data:
        user.is_active = update_data["is_active"]

    if "max_concurrent_tickets" in update_data:
        user.max_concurrent_tickets = update_data["max_concurrent_tickets"]

    user.updated_at = datetime.utcnow()
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail="用户名或邮箱已存在") from exc
    await db.refresh(user)
    return user


async def reset_user_password(db: AsyncSession, user_id: int) -> str:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    temp_password = ''.join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(12)
    )
    user.password_hash = get_password_hash(temp_password)
    user.updated_at = datetime.utcnow()

    await create_notification(
        db,
        user_id=user_id,
        type="password_reset",
        title="您的密码已被管理员重置",
        message="请使用临时密码登录后立即修改密码。",
        data={"user_id": user_id},
    )

    await db.commit()
    return temp_password
