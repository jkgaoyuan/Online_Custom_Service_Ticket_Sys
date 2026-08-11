from sqlalchemy import select

from app.models.category import Category
from app.models.notification import Notification
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


async def _create_user(db, username, role="customer"):
    user = User(
        username=username,
        email=f"{username}@example.com",
        password_hash=get_password_hash("Pass1234"),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_ticket(db, title, description, category_id, requester_id, status="open", priority="P2", assignee_id=None):
    data = TicketCreate(
        title=title,
        description=description,
        category_id=category_id,
        priority=priority,
        source="web",
        assignee_id=assignee_id,
    )
    ticket = await create_ticket(db, data, requester_id)
    if status != "open":
        ticket.status = status
        await db.commit()
        await db.refresh(ticket)
    return ticket


# API-COLLAB-001: 转交工单成功，处理人变更
async def test_transfer_ticket_success(client, agent_auth_headers, db):
    agent = await db.execute(select(User).where(User.username == "agent_test"))
    agent = agent.scalar_one()
    target_agent = await _create_user(db, "target_agent", "agent")
    customer = await _create_user(db, "customer1", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Transfer me", "Desc", category.id, customer.id,
        status="closed", assignee_id=agent.id
    )

    body = {"to_user_id": target_agent.id, "reason": "Need help"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 200
    data = r.json()
    assert data["assignee_id"] == target_agent.id


# API-COLLAB-002: 转交创建协作记录，详情可查询
async def test_transfer_creates_collaboration_record(client, agent_auth_headers, admin_auth_headers, db):
    agent = await db.execute(select(User).where(User.username == "agent_test"))
    agent = agent.scalar_one()
    target_agent = await _create_user(db, "target_agent2", "agent")
    customer = await _create_user(db, "customer2", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Transfer record", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )

    body = {"to_user_id": target_agent.id, "reason": "Please take over"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 200

    r = await client.get(f"/api/v1/tickets/{ticket.id}", headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["collaborations"] is not None
    assert len(data["collaborations"]) == 1
    assert data["collaborations"][0]["type"] == "transfer"
    assert data["collaborations"][0]["to_user"]["username"] == target_agent.username


# API-COLLAB-003: 请求协助成功，返回 201
async def test_request_assistance_success(client, agent_auth_headers, db):
    agent = await db.execute(select(User).where(User.username == "agent_test"))
    agent = agent.scalar_one()
    assist_agent = await _create_user(db, "assist_agent", "agent")
    customer = await _create_user(db, "customer3", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Need assistance", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )

    body = {"to_user_id": assist_agent.id, "reason": "Help needed"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/assist", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 201
    data = r.json()
    assert data["type"] == "assist"
    assert data["to_user"]["id"] == assist_agent.id
    assert data["to_user"]["username"] == assist_agent.username


# API-COLLAB-004: 转交后目标客服收到通知
async def test_transfer_notification_sent(client, agent_auth_headers, db):
    agent = await db.execute(select(User).where(User.username == "agent_test"))
    agent = agent.scalar_one()
    target_agent = await _create_user(db, "target_agent3", "agent")
    customer = await _create_user(db, "customer4", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Notify transfer", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )

    body = {"to_user_id": target_agent.id, "reason": "Handover"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 200

    result = await db.execute(
        select(Notification).where(
            Notification.user_id == target_agent.id,
            Notification.type == "ticket_transferred",
        )
    )
    notification = result.scalar_one_or_none()
    assert notification is not None
    assert "转交" in notification.message


# API-COLLAB-005: 转交给自己返回 400
async def test_transfer_to_self_400(client, agent_auth_headers, db):
    agent = await db.execute(select(User).where(User.username == "agent_test"))
    agent = agent.scalar_one()
    customer = await _create_user(db, "customer5", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Self transfer", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )

    body = {"to_user_id": agent.id}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 400


# API-COLLAB-006: 转交给非客服角色返回 400
async def test_transfer_to_non_agent_400(client, agent_auth_headers, db):
    agent = await db.execute(select(User).where(User.username == "agent_test"))
    agent = agent.scalar_one()
    customer = await _create_user(db, "customer6", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Transfer to customer", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )

    body = {"to_user_id": customer.id}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 400


# API-COLLAB-007: 重复请求协助返回 400
async def test_duplicate_assistance_400(client, agent_auth_headers, db):
    agent = await db.execute(select(User).where(User.username == "agent_test"))
    agent = agent.scalar_one()
    assist_agent = await _create_user(db, "assist_agent2", "agent")
    customer = await _create_user(db, "customer7", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Duplicate assist", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )

    body = {"to_user_id": assist_agent.id, "reason": "First"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/assist", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 201

    body = {"to_user_id": assist_agent.id, "reason": "Second"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/assist", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 400


# API-COLLAB-008: 转交不存在的工单返回 404
async def test_transfer_nonexistent_ticket_404(client, agent_auth_headers, db):
    body = {"to_user_id": 1}
    r = await client.post(
        "/api/v1/tickets/99999/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 404


# API-COLLAB-009: open 工单转交后变为 in_progress
async def test_transfer_open_ticket_status_change(client, agent_auth_headers, db):
    agent = await db.execute(select(User).where(User.username == "agent_test"))
    agent = agent.scalar_one()
    target_agent = await _create_user(db, "target_agent4", "agent")
    customer = await _create_user(db, "customer8", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Open transfer", "Desc", category.id, customer.id,
        status="open"
    )

    body = {"to_user_id": target_agent.id}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"
    assert r.json()["assignee_id"] == target_agent.id


# API-COLLAB-010: 客户无权转交工单，返回 403
async def test_transfer_customer_forbidden_403(client, customer_auth_headers, db):
    customer = await db.execute(select(User).where(User.username == "customer_test"))
    customer = customer.scalar_one()
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Customer transfer", "Desc", category.id, customer.id,
        status="open"
    )

    body = {"to_user_id": 1}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer", headers=customer_auth_headers, json=body
    )
    assert r.status_code == 403
