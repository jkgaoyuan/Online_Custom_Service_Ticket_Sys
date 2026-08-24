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


async def test_agent_can_view_own_resolved_ticket(client, db):
    """客服应能查看自己分配的已解决工单"""
    agent = User(username="own_agent", email="own_agent@example.com", password_hash=get_password_hash("Pass1234"), role="agent", is_active=True)
    customer = User(username="own_customer", email="own_customer@example.com", password_hash=get_password_hash("Pass1234"), role="customer", is_active=True)
    db.add(agent)
    db.add(customer)
    await db.commit()
    await db.refresh(agent)
    await db.refresh(customer)

    category = await _create_category(db)
    ticket = await _create_ticket(db, "Resolved by me", "Desc", category.id, customer.id, status="resolved", assignee_id=agent.id)

    from app.services.auth_service import create_access_token
    token = await create_access_token(agent.id)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get(f"/api/v1/tickets/{ticket.id}", headers=headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["id"] == ticket.id
    assert data["status"] == "resolved"


async def test_agent_can_view_own_closed_ticket(client, db):
    """客服应能查看自己分配的已关闭工单"""
    agent = User(username="own_agent2", email="own_agent2@example.com", password_hash=get_password_hash("Pass1234"), role="agent", is_active=True)
    customer = User(username="own_customer2", email="own_customer2@example.com", password_hash=get_password_hash("Pass1234"), role="customer", is_active=True)
    db.add(agent)
    db.add(customer)
    await db.commit()
    await db.refresh(agent)
    await db.refresh(customer)

    category = await _create_category(db)
    ticket = await _create_ticket(db, "Closed by me", "Desc", category.id, customer.id, status="closed", assignee_id=agent.id)

    from app.services.auth_service import create_access_token
    token = await create_access_token(agent.id)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get(f"/api/v1/tickets/{ticket.id}", headers=headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"


async def test_agent_can_view_own_waiting_ticket(client, db):
    """客服应能查看自己分配的等待客户工单"""
    agent = User(username="own_agent3", email="own_agent3@example.com", password_hash=get_password_hash("Pass1234"), role="agent", is_active=True)
    customer = User(username="own_customer3", email="own_customer3@example.com", password_hash=get_password_hash("Pass1234"), role="customer", is_active=True)
    db.add(agent)
    db.add(customer)
    await db.commit()
    await db.refresh(agent)
    await db.refresh(customer)

    category = await _create_category(db)
    ticket = await _create_ticket(db, "Waiting by me", "Desc", category.id, customer.id, status="waiting", assignee_id=agent.id)

    from app.services.auth_service import create_access_token
    token = await create_access_token(agent.id)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get(f"/api/v1/tickets/{ticket.id}", headers=headers)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"


async def test_agent_can_update_own_ticket_to_resolved(client, db):
    """客服应能将自己处理中的工单标记为已解决"""
    agent = User(username="own_agent4", email="own_agent4@example.com", password_hash=get_password_hash("Pass1234"), role="agent", is_active=True)
    customer = User(username="own_customer4", email="own_customer4@example.com", password_hash=get_password_hash("Pass1234"), role="customer", is_active=True)
    db.add(agent)
    db.add(customer)
    await db.commit()
    await db.refresh(agent)
    await db.refresh(customer)

    category = await _create_category(db)
    ticket = await _create_ticket(db, "In progress", "Desc", category.id, customer.id, status="in_progress", assignee_id=agent.id)

    from app.services.auth_service import create_access_token
    token = await create_access_token(agent.id)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(f"/api/v1/tickets/{ticket.id}/status", headers=headers, json={"status": "resolved"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    # 更新后仍然能访问
    r2 = await client.get(f"/api/v1/tickets/{ticket.id}", headers=headers)
    assert r2.status_code == 200, f"Expected 200 after resolve, got {r2.status_code}: {r2.text}"
    data = r2.json()
    assert data["status"] == "resolved"


async def test_claim_open_ticket_sets_assignee(client, db):
    """接单（open→in_progress）自动设置负责人"""
    agent = User(username="claim_agent", email="claim_agent@example.com", password_hash=get_password_hash("Pass1234"), role="agent", is_active=True)
    customer = User(username="claim_customer", email="claim_customer@example.com", password_hash=get_password_hash("Pass1234"), role="customer", is_active=True)
    db.add(agent)
    db.add(customer)
    await db.commit()
    await db.refresh(agent)
    await db.refresh(customer)

    category = await _create_category(db)
    ticket = await _create_ticket(db, "Open to claim", "Desc", category.id, customer.id, status="open", assignee_id=None)

    from app.services.auth_service import create_access_token
    token = await create_access_token(agent.id)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(f"/api/v1/tickets/{ticket.id}/status", headers=headers, json={"status": "in_progress"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["status"] == "in_progress"
    assert data["assignee_id"] == agent.id


async def test_cannot_resolve_unassigned_ticket(client, db):
    """无负责人工单不能流转到 resolved"""
    agent = User(username="resolve_agent", email="resolve_agent@example.com", password_hash=get_password_hash("Pass1234"), role="agent", is_active=True)
    customer = User(username="resolve_customer", email="resolve_customer@example.com", password_hash=get_password_hash("Pass1234"), role="customer", is_active=True)
    db.add(agent)
    db.add(customer)
    await db.commit()
    await db.refresh(agent)
    await db.refresh(customer)

    category = await _create_category(db)
    ticket = await _create_ticket(db, "No assignee", "Desc", category.id, customer.id, status="in_progress", assignee_id=None)

    from app.services.auth_service import create_access_token
    token = await create_access_token(agent.id)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(f"/api/v1/tickets/{ticket.id}/status", headers=headers, json={"status": "resolved"})
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
    assert "未分配负责人" in r.json()["detail"]
