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

async def _create_ticket(db, title, description, category_id, requester_id, status="open", priority="P2", assignee_id=None):
    data = TicketCreate(title=title, description=description, category_id=category_id, priority=priority, source="web", assignee_id=assignee_id)
    ticket = await create_ticket(db, data, requester_id)
    if status != "open":
        ticket.status = status
        await db.commit()
        await db.refresh(ticket)
    return ticket


async def test_reply_ticket_success(client, agent_auth_headers, open_ticket, db):
    body = {"content": "请尝试清除缓存", "is_internal": False}
    r = await client.post(f"/api/v1/tickets/{open_ticket.id}/replies", headers=agent_auth_headers, json=body)
    assert r.status_code == 201
    data = r.json()
    assert data["content"] == "请尝试清除缓存"
    assert data["is_internal"] == False
    # Verify status transition
    ticket_r = await client.get(f"/api/v1/tickets/{open_ticket.id}", headers=agent_auth_headers)
    ticket_data = ticket_r.json()
    assert ticket_data["status"] == "in_progress"
    assert ticket_data["assignee_id"] is not None


async def test_internal_reply_hidden_from_customer(client, agent_auth_headers, customer_auth_headers, db):
    # Get customer_test user and create a ticket they own
    result = await db.execute(select(User).where(User.username == "customer_test"))
    customer = result.scalar_one()
    category = await _create_category(db)
    ticket = await _create_ticket(db, "Internal ticket", "Desc", category.id, customer.id)
    # First reply takes the ticket to in_progress
    body = {"content": "内部处理中", "is_internal": True}
    r = await client.post(f"/api/v1/tickets/{ticket.id}/replies", headers=agent_auth_headers, json=body)
    assert r.status_code == 201
    # Customer lists replies
    r = await client.get(f"/api/v1/tickets/{ticket.id}/replies", headers=customer_auth_headers)
    assert r.status_code == 200
    replies = r.json()
    assert all(reply["is_internal"] == False for reply in replies)


async def test_reply_not_found_ticket_404(client, agent_auth_headers, db):
    body = {"content": "test"}
    r = await client.post("/api/v1/tickets/99999/replies", headers=agent_auth_headers, json=body)
    assert r.status_code == 404
    assert r.json()["detail"] == "工单不存在"


async def test_reply_empty_content_422(client, agent_auth_headers, open_ticket, db):
    body = {"content": ""}
    r = await client.post(f"/api/v1/tickets/{open_ticket.id}/replies", headers=agent_auth_headers, json=body)
    assert r.status_code == 422


async def test_customer_reply_own_ticket(client, customer_auth_headers, db):
    # Get customer_test user and create a ticket they own
    result = await db.execute(select(User).where(User.username == "customer_test"))
    customer = result.scalar_one()
    category = await _create_category(db)
    ticket = await _create_ticket(db, "Own ticket", "Desc", category.id, customer.id)
    body = {"content": "问题已解决，谢谢"}
    r = await client.post(f"/api/v1/tickets/{ticket.id}/replies", headers=customer_auth_headers, json=body)
    assert r.status_code == 201
    data = r.json()
    assert data["content"] == "问题已解决，谢谢"
    assert data["is_internal"] == False


async def test_customer_reply_other_ticket_403(client, customer_auth_headers, db):
    # Create another customer and their ticket
    another = User(username="other_customer", email="other@example.com", password_hash=get_password_hash("Pass1234"), role="customer", is_active=True)
    db.add(another)
    await db.commit()
    await db.refresh(another)
    category = await _create_category(db)
    ticket = await _create_ticket(db, "Other ticket", "Desc", category.id, another.id)
    body = {"content": "test"}
    r = await client.post(f"/api/v1/tickets/{ticket.id}/replies", headers=customer_auth_headers, json=body)
    assert r.status_code == 403
    assert r.json()["detail"] == "无权访问该工单"


async def test_customer_reply_waiting_ticket_becomes_in_progress(client, customer_auth_headers, db):
    """客户回复 waiting 状态的工单，状态自动恢复为 in_progress"""
    result = await db.execute(select(User).where(User.username == "customer_test"))
    customer = result.scalar_one()
    category = await _create_category(db)
    # 创建一个 agent 并分配给 waiting 工单
    agent = User(
        username="waiting_agent",
        email="waiting_agent@example.com",
        password_hash=get_password_hash("Pass1234"),
        role="agent",
        is_active=True,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    ticket = await _create_ticket(db, "Waiting ticket", "Desc", category.id, customer.id, status="waiting", assignee_id=agent.id)
    body = {"content": "我已补充资料", "is_internal": False}
    r = await client.post(f"/api/v1/tickets/{ticket.id}/replies", headers=customer_auth_headers, json=body)
    assert r.status_code == 201
    data = r.json()
    assert data["content"] == "我已补充资料"
    # 验证状态变为 in_progress
    ticket_r = await client.get(f"/api/v1/tickets/{ticket.id}", headers=customer_auth_headers)
    ticket_data = ticket_r.json()
    assert ticket_data["status"] == "in_progress"
