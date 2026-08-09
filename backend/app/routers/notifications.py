from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.notification import NotificationResponse
from app.services.notification_service import (
    get_unread_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)

router = APIRouter()


@router.get("/notifications", response_model=dict)
async def list_notifications(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = await get_unread_notifications(db, current_user.id, limit=limit)
    unread_count = sum(1 for n in items if not n.is_read)
    return {
        "items": [NotificationResponse.model_validate(n).model_dump() for n in items],
        "unread_count": unread_count,
    }


@router.post("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def read_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await mark_notification_read(db, notification_id, current_user.id)
    return None


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def read_all_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await mark_all_notifications_read(db, current_user.id)
    return None
