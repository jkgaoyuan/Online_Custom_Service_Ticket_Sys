from datetime import datetime, timedelta
from sqlalchemy import select

from app.models.notification import Notification
from app.models.user import User
from app.services.notification_service import (
    count_unread_notifications,
    create_notification,
    get_user_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)


# ===== Service layer tests =====

async def test_create_notification(db):
    from tests.conftest import _create_user

    user = await _create_user(db, "notif_user", "customer")
    notif = await create_notification(
        db, user.id, "sla_breach", "Title", "Message", {"ticket_id": 1}
    )

    assert notif.user_id == user.id
    assert notif.type == "sla_breach"
    assert notif.title == "Title"
    assert notif.message == "Message"
    assert notif.data == {"ticket_id": 1}

    await db.commit()
    await db.refresh(notif)
    assert notif.id is not None
    assert notif.is_read is False


async def test_get_user_notifications(db):
    from tests.conftest import _create_user

    user = await _create_user(db, "notif_user2", "customer")

    notif1 = await create_notification(db, user.id, "type1", "First", "Msg1")
    notif1.created_at = datetime.utcnow() - timedelta(hours=2)

    notif2 = await create_notification(db, user.id, "type2", "Second", "Msg2")
    notif2.created_at = datetime.utcnow() - timedelta(hours=1)

    notif3 = await create_notification(db, user.id, "type3", "Third", "Msg3")
    notif3.created_at = datetime.utcnow() - timedelta(hours=3)

    await db.commit()

    items = await get_user_notifications(db, user.id, limit=50)
    assert len(items) == 3
    titles = [n.title for n in items]
    assert titles == ["Second", "First", "Third"]


async def test_mark_notification_read(db):
    from tests.conftest import _create_user

    user = await _create_user(db, "notif_user3", "customer")
    notif = await create_notification(db, user.id, "type", "Title", "Message")
    await db.commit()
    await db.refresh(notif)

    ok = await mark_notification_read(db, notif.id, user.id)
    assert ok is True

    await db.commit()

    result = await db.execute(select(Notification).where(Notification.id == notif.id))
    updated = result.scalar_one()
    assert updated.is_read is True


async def test_mark_all_notifications_read(db):
    from tests.conftest import _create_user

    user = await _create_user(db, "notif_user4", "customer")

    notif1 = await create_notification(db, user.id, "type1", "Title1", "Msg1")
    notif2 = await create_notification(db, user.id, "type2", "Title2", "Msg2")
    notif3 = await create_notification(db, user.id, "type3", "Title3", "Msg3")
    notif3.is_read = True

    await db.commit()

    count = await mark_all_notifications_read(db, user.id)
    assert count == 2

    await db.commit()

    result = await db.execute(select(Notification).where(Notification.user_id == user.id))
    items = result.scalars().all()
    assert all(n.is_read for n in items)


# ===== API tests =====

async def test_api_list_notifications(client, customer_auth_headers, db):
    result = await db.execute(select(User).where(User.username == "customer_test"))
    user = result.scalar_one()

    notif1 = await create_notification(
        db, user.id, "sla_warn", "SLA Warning", "Ticket approaching deadline"
    )
    notif2 = await create_notification(
        db, user.id, "assigned", "Assigned", "You have a new ticket"
    )
    await db.commit()

    r = await client.get("/api/v1/notifications", headers=customer_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "unread_count" in data
    assert len(data["items"]) == 2
    assert data["unread_count"] == 2


async def test_api_mark_read_own_only(client, supervisor_auth_headers, db):
    from tests.conftest import _create_user

    customer = await _create_user(db, "notif_customer", "customer")
    notif = await create_notification(db, customer.id, "type", "Title", "Message")
    await db.commit()
    await db.refresh(notif)

    r = await client.post(
        f"/api/v1/notifications/{notif.id}/read", headers=supervisor_auth_headers
    )
    assert r.status_code == 404

    result = await db.execute(select(Notification).where(Notification.id == notif.id))
    updated = result.scalar_one()
    assert updated.is_read is False


async def test_get_user_notifications_include_read(db):
    from tests.conftest import _create_user

    user = await _create_user(db, "notif_include_read", "customer")

    notif_unread = await create_notification(db, user.id, "type1", "Unread", "Msg1")
    notif_read = await create_notification(db, user.id, "type2", "Read", "Msg2")
    notif_read.is_read = True

    await db.commit()

    unread_items = await get_user_notifications(db, user.id, include_read=False)
    assert len(unread_items) == 1
    assert unread_items[0].title == "Unread"

    all_items = await get_user_notifications(db, user.id, include_read=True)
    assert len(all_items) == 2


async def test_get_user_notifications_pagination(db):
    from tests.conftest import _create_user

    user = await _create_user(db, "notif_paginate", "customer")

    for i in range(5):
        notif = await create_notification(db, user.id, f"type{i}", f"Notif{i}", "Msg")
        notif.created_at = datetime.utcnow() - timedelta(minutes=i)

    await db.commit()

    page1 = await get_user_notifications(db, user.id, limit=2, offset=0)
    assert len(page1) == 2
    assert page1[0].title == "Notif0"
    assert page1[1].title == "Notif1"

    page2 = await get_user_notifications(db, user.id, limit=2, offset=2)
    assert len(page2) == 2
    assert page2[0].title == "Notif2"
    assert page2[1].title == "Notif3"

    page3 = await get_user_notifications(db, user.id, limit=2, offset=4)
    assert len(page3) == 1
    assert page3[0].title == "Notif4"


async def test_count_unread_notifications(db):
    from tests.conftest import _create_user

    user = await _create_user(db, "notif_count", "customer")

    await create_notification(db, user.id, "type1", "A", "Msg1")
    await create_notification(db, user.id, "type2", "B", "Msg2")
    notif_read = await create_notification(db, user.id, "type3", "C", "Msg3")
    notif_read.is_read = True

    await db.commit()

    count = await count_unread_notifications(db, user.id)
    assert count == 2


async def test_api_unread_count_accurate(client, customer_auth_headers, db):
    result = await db.execute(select(User).where(User.username == "customer_test"))
    user = result.scalar_one()

    for i in range(5):
        await create_notification(db, user.id, f"type{i}", f"Notif{i}", "Msg")

    await db.commit()

    r = await client.get("/api/v1/notifications?limit=2", headers=customer_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 2
    assert data["unread_count"] == 5


async def test_api_mark_read_not_found(client, customer_auth_headers):
    r = await client.post(
        "/api/v1/notifications/999999/read", headers=customer_auth_headers
    )
    assert r.status_code == 404
