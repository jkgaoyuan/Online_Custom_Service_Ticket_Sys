import pytest

from app.models.agent_skill import AgentSkill
from app.models.category import Category
from app.models.user import User
from app.schemas.ticket import TicketCreate
from app.services.auth_service import create_access_token
from app.services.ticket_service import create_ticket
from app.utils.security import get_password_hash


# ===== 辅助工厂函数（自包含，减少耦合） =====


async def _create_user(db, username, role="customer", password="Pass1234") -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        password_hash=get_password_hash(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_category(db) -> Category:
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
        await db.commit()
        await db.refresh(ticket)
    return ticket


def _auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


# ===== 用例 1: 客户-客服-主管 全生命周期 =====


@pytest.mark.asyncio
async def test_e2e_customer_agent_supervisor_ticket_lifecycle(client, db):
    """
    E2E-001: 串联注册 -> 创建工单 -> 客服回复 -> 标记resolved -> 主管关闭 ->
    满意度通知 -> 提交评价 -> 最终验证
    """
    # --- 1. 客户注册并登录 ---
    register_body = {
        "username": "cust_e2e",
        "email": "cust_e2e@example.com",
        "password": "Pass1234",
    }
    r = await client.post("/api/v1/auth/register", json=register_body)
    assert r.status_code == 201
    customer = r.json()
    assert customer["role"] == "customer"

    r = await client.post("/api/v1/auth/login", json={"username": "cust_e2e", "password": "Pass1234"})
    assert r.status_code == 200
    login_data = r.json()
    customer_token = login_data["access_token"]
    customer_headers = _auth_headers(customer_token)

    # --- 2. 客户创建工单 ---
    category = await _create_category(db)
    ticket_body = {
        "title": "无法登录系统",
        "description": "点击登录按钮没有任何反应",
        "category_id": category.id,
        "priority": "P1",
        "source": "web",
    }
    r = await client.post("/api/v1/tickets", headers=customer_headers, json=ticket_body)
    assert r.status_code == 201
    ticket = r.json()
    assert ticket["status"] == "open"
    assert ticket["ticket_no"].startswith("TK-")
    ticket_id = ticket["id"]

    # --- 3. 客服登录并查看工单 ---
    agent = await _create_user(db, "agent_e2e", "agent")
    agent_token = await create_access_token(agent.id)
    agent_headers = _auth_headers(agent_token)

    r = await client.get(f"/api/v1/tickets/{ticket_id}", headers=agent_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == ticket_id
    assert data["status"] == "open"

    # --- 4. 客服回复工单 ---
    reply_body = {"content": "请尝试清除浏览器缓存后重试", "is_internal": False}
    r = await client.post(f"/api/v1/tickets/{ticket_id}/replies", headers=agent_headers, json=reply_body)
    assert r.status_code == 201
    reply_data = r.json()
    assert reply_data["content"] == "请尝试清除浏览器缓存后重试"

    # 再次 GET 工单，验证状态变为 in_progress
    r = await client.get(f"/api/v1/tickets/{ticket_id}", headers=agent_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "in_progress"
    assert data["assignee_id"] is not None

    # --- 5. 客服标记 resolved ---
    r = await client.post(f"/api/v1/tickets/{ticket_id}/status", headers=agent_headers, json={"status": "resolved"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "resolved"
    assert data["resolved_at"] is not None

    # --- 6. 主管关闭工单 ---
    supervisor = await _create_user(db, "supervisor_e2e", "supervisor")
    supervisor_token = await create_access_token(supervisor.id)
    supervisor_headers = _auth_headers(supervisor_token)

    r = await client.post(f"/api/v1/tickets/{ticket_id}/status", headers=supervisor_headers, json={"status": "closed"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "closed"

    # --- 7. 客户收到满意度邀请通知 ---
    r = await client.get("/api/v1/notifications", headers=customer_headers)
    assert r.status_code == 200
    notif_data = r.json()
    assert any(n["type"] == "satisfaction_invite" for n in notif_data["items"])

    # --- 8. 客户提交满意度评价 ---
    satisfaction_body = {"rating": "satisfied", "note": "服务很好"}
    r = await client.post(f"/api/v1/tickets/{ticket_id}/satisfaction", headers=customer_headers, json=satisfaction_body)
    assert r.status_code == 200
    data = r.json()
    assert data["satisfaction"] == "satisfied"

    # --- 9. 最终验证 ---
    r = await client.get(f"/api/v1/tickets/{ticket_id}", headers=customer_headers)
    assert r.status_code == 200
    final = r.json()
    assert final["status"] == "closed"
    assert final["satisfaction"] == "satisfied"
    assert final["satisfaction_note"] is not None
    assert final["satisfaction_note"] != ""


# ===== 用例 2: 自动分派到结案 =====


@pytest.mark.asyncio
async def test_e2e_auto_dispatch_to_resolution(client, db):
    """
    E2E-002: 创建分类+技能客服 -> 客户创建工单(auto_dispatch=true) ->
    自动分配 -> agent回复 -> resolved -> 主管关闭 -> 客户评价 -> 验证dispatch log
    """
    # --- 1. 创建分类和技能客服 ---
    category = await _create_category(db)
    agent = await _create_user(db, "agent_dispatch", "agent")
    db.add(AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=5))
    await db.commit()

    # --- 2. 客户创建工单并开启 auto_dispatch ---
    customer = await _create_user(db, "cust_dispatch", "customer")
    customer_token = await create_access_token(customer.id)
    customer_headers = _auth_headers(customer_token)

    ticket_body = {
        "title": "自动分派测试工单",
        "description": "测试自动分派流程",
        "category_id": category.id,
        "priority": "P2",
        "source": "web",
        "auto_dispatch": True,
    }
    r = await client.post("/api/v1/tickets", headers=customer_headers, json=ticket_body)
    assert r.status_code == 201
    ticket = r.json()
    ticket_id = ticket["id"]
    assert ticket["assignee_id"] == agent.id
    assert ticket["status"] == "in_progress"

    # --- 3. 被分配的 agent 登录并回复 ---
    agent_token = await create_access_token(agent.id)
    agent_headers = _auth_headers(agent_token)

    reply_body = {"content": "已收到工单，正在处理", "is_internal": False}
    r = await client.post(f"/api/v1/tickets/{ticket_id}/replies", headers=agent_headers, json=reply_body)
    assert r.status_code == 201

    # --- 4. agent 流转状态到 resolved ---
    r = await client.post(f"/api/v1/tickets/{ticket_id}/status", headers=agent_headers, json={"status": "resolved"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "resolved"

    # --- 5. 主管关闭工单 ---
    supervisor = await _create_user(db, "supervisor_dispatch", "supervisor")
    supervisor_token = await create_access_token(supervisor.id)
    supervisor_headers = _auth_headers(supervisor_token)

    r = await client.post(f"/api/v1/tickets/{ticket_id}/status", headers=supervisor_headers, json={"status": "closed"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "closed"

    # --- 6. 客户提交评价 ---
    satisfaction_body = {"rating": "satisfied", "note": "自动分派很及时"}
    r = await client.post(f"/api/v1/tickets/{ticket_id}/satisfaction", headers=customer_headers, json=satisfaction_body)
    assert r.status_code == 200
    data = r.json()
    assert data["satisfaction"] == "satisfied"

    # --- 7. 验证 dispatch log ---
    r = await client.get(f"/api/v1/admin/dispatch-logs?ticket_id={ticket_id}", headers=supervisor_headers)
    assert r.status_code == 200
    logs = r.json()
    assert len(logs) >= 1
    assert any(log["ticket_id"] == ticket_id for log in logs)
