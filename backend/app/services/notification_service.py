from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sse import send_event
from app.models.notification import Notification


async def create_notification(
    db: AsyncSession,
    user_id: int,
    type: str,
    title: str,
    message: str,
    data: dict | None = None,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        data=data or {},
    )
    db.add(notif)
    await db.flush()
    await send_event(
        user_id,
        "new_notification",
        {
            "id": notif.id,
            "type": type,
            "title": title,
            "message": message,
        },
    )
    return notif


async def get_user_notifications(
    db: AsyncSession, user_id: int, limit: int = 50, offset: int = 0, include_read: bool = False
) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if not include_read:
        stmt = stmt.where(Notification.is_read.is_(False))
    result = await db.execute(stmt)
    return result.scalars().all()


async def count_unread_notifications(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
    )
    return len(result.scalars().all())


async def mark_notification_read(db: AsyncSession, notification_id: int, user_id: int) -> bool:
    result = await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == user_id)
        .values(is_read=True)
    )
    return result.rowcount > 0


async def mark_all_notifications_read(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    return result.rowcount
