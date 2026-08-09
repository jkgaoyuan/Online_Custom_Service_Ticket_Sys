# Task 3 Brief: Notification Service and REST API

## Where This Fits

This is Task 3 of 6 for T006. Task 1 created the `Notification` model. This task builds the notification service and REST API.

## Interfaces from Earlier Tasks

- `Notification` model at `app.models.notification`
- `app.main.py` already registers routers via `app.include_router(...)`

## Requirements

### Step 1: Create `backend/app/schemas/notification.py`

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    message: str
    data: dict
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### Step 2: Create `backend/app/services/notification_service.py`

```python
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
```

### Step 3: Create `backend/app/routers/notifications.py`

```python
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
```

### Step 4: Modify `backend/app/main.py`

Add import: `from app.routers import auth, categories, dispatch, notifications, sla, tickets, webhooks`

Add router registration BEFORE the existing routers (order doesn't matter much, but keep consistent):
```python
app.include_router(notifications.router, prefix="/api/v1", tags=["Notifications"])
```

Note: `sla` router does not exist yet (Task 5), but the import already references it. If the import fails because `app/routers/sla.py` does not exist, ONLY import `notifications` for now and leave `sla` out. Do NOT create a placeholder `sla.py` router in this task.

### Step 5-6: Write tests in `backend/tests/test_notifications.py`

Write these tests:
- `test_create_notification` — service layer creates notification, asserts fields
- `test_get_unread_notifications` — returns items in desc order
- `test_mark_notification_read` — marks own notification read
- `test_mark_all_notifications_read` — marks all unread as read
- `test_api_list_notifications` — GET /api/v1/notifications returns 200 with items/unread_count
- `test_api_mark_read_own_only` — supervisor cannot mark customer's notification (WHERE filters, no effect)

Run: `pytest -p no:anyio tests/test_notifications.py -v`
Expected: all tests PASS

### Step 7: Commit

```bash
git add backend/app/services/notification_service.py backend/app/routers/notifications.py backend/app/schemas/notification.py backend/app/main.py backend/tests/test_notifications.py
git commit -m "feat(t006): notification service and REST API"
```

## Global Constraints

- `create_notification` does NOT call `db.flush()` or `db.commit()` internally.
- Notification API endpoints require `get_current_user` (any authenticated user).
- `mark_notification_read` filters by both `notification_id` AND `user_id` so users can only affect their own notifications.
- All tests use `-p no:anyio`.
- Do NOT modify any files not listed above.
- Do NOT create placeholder `sla.py` router.

## Report

Write your report to `.claude/task-3-report.md` with status, files touched, test command + output, concerns.
