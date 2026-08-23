import asyncio
import json
from datetime import datetime

import pytest
from sqlalchemy import select

from app.core.sse import add_client, send_event
from app.models.agent_skill import AgentSkill
from app.models.category import Category
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate
from app.services.dispatch_service import auto_assign
from app.services.ticket_service import create_ticket
from app.utils.security import get_password_hash


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


async def _create_category(db):
    category = Category(name="故障", code="bug", default_priority="P2")
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


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
        if status in ("resolved", "closed"):
            ticket.resolved_at = datetime.utcnow()
        await db.commit()
        await db.refresh(ticket)
    return ticket


# ===== Agent Stats API =====

# M2-T7-01: agent stats 返回正确统计
async def test_agent_stats_success(client, agent_auth_headers, db):
    agent_result = await db.execute(select(User).where(User.username == "agent_test"))
    agent = agent_result.scalar_one()
    customer = await _create_user(db, "stats_customer", "customer")
    category = await _create_category(db)

    # 创建不同状态的工单
    await _create_ticket(db, "Open ticket", "desc", category.id, customer.id, status="open", assignee_id=agent.id)
    await _create_ticket(db, "In progress 1", "desc", category.id, customer.id, status="in_progress", assignee_id=agent.id)
    await _create_ticket(db, "In progress 2", "desc", category.id, customer.id, status="in_progress", assignee_id=agent.id)
    await _create_ticket(db, "Resolved ticket", "desc", category.id, customer.id, status="resolved", assignee_id=agent.id)
    await _create_ticket(db, "Closed ticket", "desc", category.id, customer.id, status="closed", assignee_id=agent.id)
    await _create_ticket(db, "Waiting ticket", "desc", category.id, customer.id, status="waiting", assignee_id=agent.id)

    r = await client.get("/api/v1/agent/stats", headers=agent_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["open"] == 1
    assert data["in_progress"] == 2
    assert data["resolved"] == 2
    assert data["waiting"] == 1


# M2-T7-02: supervisor 可访问 agent stats
async def test_agent_stats_supervisor_allowed(client, supervisor_auth_headers, db):
    r = await client.get("/api/v1/agent/stats", headers=supervisor_auth_headers)
    assert r.status_code == 200


# M2-T7-03: customer 不可访问 agent stats
async def test_agent_stats_customer_forbidden(client, customer_auth_headers, db):
    r = await client.get("/api/v1/agent/stats", headers=customer_auth_headers)
    assert r.status_code == 403


# ===== SSE Events =====

# M2-T7-04: auto_assign 后发送 SSE 事件
async def test_auto_assign_sends_sse(db):
    agent = await _create_user(db, "sse_agent", "agent")
    customer = await _create_user(db, "sse_customer", "customer")
    category = await _create_category(db)
    db.add(AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=5))
    await db.commit()
    ticket = await _create_ticket(db, "SSE ticket", "desc", category.id, customer.id)

    client_id, queue = await add_client(agent.id)
    await auto_assign(db, ticket)
    await db.commit()

    # 检查 ticket_assigned 事件
    payload1 = await asyncio.wait_for(queue.get(), timeout=1.0)
    event1 = json.loads(payload1)
    assert event1["type"] == "ticket_assigned"
    assert event1["data"]["ticket_id"] == ticket.id
    assert event1["data"]["ticket_no"] == ticket.ticket_no

    # 检查 stats_update 事件
    payload2 = await asyncio.wait_for(queue.get(), timeout=1.0)
    event2 = json.loads(payload2)
    assert event2["type"] == "stats_update"


# M2-T7-05: 手动 assign 后发送 SSE 事件
async def test_assign_ticket_sends_sse(client, supervisor_auth_headers, db):
    agent = await _create_user(db, "manual_sse_agent", "agent")
    customer = await _create_user(db, "manual_sse_customer", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "Manual SSE", "desc", category.id, customer.id, status="open")

    client_id, queue = await add_client(agent.id)

    body = {"assignee_id": agent.id}
    r = await client.post(f"/api/v1/tickets/{ticket.id}/assign", headers=supervisor_auth_headers, json=body)
    assert r.status_code == 200

    payload1 = await asyncio.wait_for(queue.get(), timeout=1.0)
    event1 = json.loads(payload1)
    assert event1["type"] == "ticket_assigned"
    assert event1["data"]["ticket_id"] == ticket.id

    payload2 = await asyncio.wait_for(queue.get(), timeout=1.0)
    event2 = json.loads(payload2)
    assert event2["type"] == "stats_update"


# M2-T7-06: update status 后给 assignee 发送 stats_update
async def test_update_status_sends_sse(client, agent_auth_headers, db):
    agent_result = await db.execute(select(User).where(User.username == "agent_test"))
    agent = agent_result.scalar_one()
    customer = await _create_user(db, "status_sse_customer", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "Status SSE", "desc", category.id, customer.id, status="open", assignee_id=agent.id)

    client_id, queue = await add_client(agent.id)

    body = {"status": "in_progress"}
    r = await client.post(f"/api/v1/tickets/{ticket.id}/status", headers=agent_auth_headers, json=body)
    assert r.status_code == 200

    payload = await asyncio.wait_for(queue.get(), timeout=1.0)
    event = json.loads(payload)
    assert event["type"] == "stats_update"


# M2-T7-07: send_event 直接调用测试（无客户端时不报错）
async def test_send_event_no_client_does_not_raise():
    # user_id 999 不存在于 sse_clients，应静默返回
    await send_event(999, "test_event", {"foo": "bar"})
