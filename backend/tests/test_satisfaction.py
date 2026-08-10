from datetime import datetime

from sqlalchemy import select

from app.models.category import Category
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate
from app.services.ticket_service import create_ticket
from app.utils.security import get_password_hash


async def _create_category(db):
    category = Category(name="故障", code="bug", default_priority="P2")
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def _create_closed_ticket(db, customer_id, category_id):
    ticket = await create_ticket(
        db,
        TicketCreate(title="测试工单", description="描述", category_id=category_id, priority="P2"),
        customer_id,
    )
    ticket.status = "closed"
    ticket.closed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(ticket)
    return ticket


# === P0 正向 ===

# SAT-001: 客户对已关闭工单提交评价成功
async def test_submit_satisfaction_closed_ticket_200(client, customer_auth_headers, db):
    category = await _create_category(db)
    customer = (await db.execute(select(User).where(User.username == "customer_test"))).scalar_one()
    ticket = await _create_closed_ticket(db, customer.id, category.id)

    body = {"rating": "satisfied", "note": "服务很好"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction",
        headers=customer_auth_headers,
        json=body,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["satisfaction"] == "satisfied"
    assert data["satisfaction_note"] == "服务很好"
    assert data["satisfaction_at"] is not None


# SAT-002: 评价 note 为空也可提交
async def test_submit_satisfaction_no_note_200(client, customer_auth_headers, db):
    category = await _create_category(db)
    customer = (await db.execute(select(User).where(User.username == "customer_test"))).scalar_one()
    ticket = await _create_closed_ticket(db, customer.id, category.id)

    body = {"rating": "neutral"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction",
        headers=customer_auth_headers,
        json=body,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["satisfaction"] == "neutral"
    assert data["satisfaction_note"] is None


# SAT-003: 关闭工单时触发通知
async def test_close_ticket_triggers_notification(client, admin_auth_headers, customer_auth_headers, db):
    category = await _create_category(db)
    customer = (await db.execute(select(User).where(User.username == "customer_test"))).scalar_one()
    ticket = await create_ticket(
        db, TicketCreate(title="t", description="d", category_id=category.id, priority="P2"), customer.id
    )
    # 流转到 closed
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/status",
        headers=admin_auth_headers,
        json={"status": "closed"},
    )
    assert r.status_code == 200
    # 查询通知
    r = await client.get("/api/v1/notifications", headers=customer_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert any(n["type"] == "satisfaction_invite" for n in data["items"])


# === P0 异常 ===

# SAT-004: 未关闭工单提交评价 400
async def test_submit_satisfaction_open_ticket_400(client, customer_auth_headers, db):
    category = await _create_category(db)
    customer = (await db.execute(select(User).where(User.username == "customer_test"))).scalar_one()
    ticket = await create_ticket(
        db, TicketCreate(title="t", description="d", category_id=category.id, priority="P2"), customer.id
    )

    body = {"rating": "satisfied"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction",
        headers=customer_auth_headers,
        json=body,
    )
    assert r.status_code == 400
    assert "未关闭" in r.json()["detail"]


# SAT-005: 非本人工单提交评价 403
async def test_submit_satisfaction_other_user_403(client, admin_auth_headers, db):
    category = await _create_category(db)
    # 创建另一个客户
    other = User(username="other", email="other@test.com", password_hash=get_password_hash("pass"), role="customer")
    db.add(other)
    await db.commit()
    await db.refresh(other)
    ticket = await _create_closed_ticket(db, other.id, category.id)

    body = {"rating": "satisfied"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction",
        headers=admin_auth_headers,  # admin 不是 requester
        json=body,
    )
    assert r.status_code == 403
    assert "只能评价自己的工单" in r.json()["detail"]


# SAT-006: 已评价工单再次提交 400
async def test_submit_satisfaction_already_rated_400(client, customer_auth_headers, db):
    category = await _create_category(db)
    customer = (await db.execute(select(User).where(User.username == "customer_test"))).scalar_one()
    ticket = await _create_closed_ticket(db, customer.id, category.id)
    ticket.satisfaction = "satisfied"
    ticket.satisfaction_at = datetime.utcnow()
    await db.commit()

    body = {"rating": "neutral"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction",
        headers=customer_auth_headers,
        json=body,
    )
    assert r.status_code == 400
    assert "已评价" in r.json()["detail"]


# SAT-007: 无效 rating 422
async def test_submit_satisfaction_invalid_rating_422(client, customer_auth_headers, db):
    category = await _create_category(db)
    customer = (await db.execute(select(User).where(User.username == "customer_test"))).scalar_one()
    ticket = await _create_closed_ticket(db, customer.id, category.id)

    body = {"rating": "excellent"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction",
        headers=customer_auth_headers,
        json=body,
    )
    assert r.status_code == 422


# SAT-008: note 超长截断
async def test_submit_satisfaction_long_note_truncated_200(client, customer_auth_headers, db):
    category = await _create_category(db)
    customer = (await db.execute(select(User).where(User.username == "customer_test"))).scalar_one()
    ticket = await _create_closed_ticket(db, customer.id, category.id)

    body = {"rating": "satisfied", "note": "x" * 600}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction",
        headers=customer_auth_headers,
        json=body,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["satisfaction_note"]) == 500
