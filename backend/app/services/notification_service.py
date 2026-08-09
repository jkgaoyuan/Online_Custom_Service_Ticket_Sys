from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

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
    # 不自行 flush，由调用方统一 commit
    return notif


async def get_unread_notifications(
    db: AsyncSession, user_id: int, limit: int = 50
) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


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
