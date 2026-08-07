from sqlalchemy import select

from app.models.category import Category
from app.models.user import User


async def _create_category(db):
    category = Category(name="故障", code="bug", default_priority="P2")
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


# ===== P0 正向 =====

# API-TICKET-001: 客户创建工单成功
async def test_create_ticket_success(client, customer_auth_headers, db):
    category = await _create_category(db)
    body = {
        "title": "无法登录",
        "description": "点击登录按钮无响应",
        "category_id": category.id,
        "priority": "P1",
    }
    r = await client.post(
        "/api/v1/tickets", headers=customer_auth_headers, json=body
    )
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "无法登录"
    assert data["status"] == "open"
    assert data["priority"] == "P1"
    assert data["source"] == "web"
    assert data["ticket_no"].startswith("TK-")

    result = await db.execute(
        select(User).where(User.username == "customer_test")
    )
    customer = result.scalar_one()
    assert data["requester_id"] == customer.id


# API-TICKET-004: 查询工单列表成功
async def test_list_tickets_success(client, customer_auth_headers, db):
    r = await client.get("/api/v1/tickets", headers=customer_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "items" in data


# ===== P0 异常 =====

# API-TICKET-002: 未认证创建工单 401
async def test_create_ticket_unauthorized_401(client, db):
    body = {
        "title": "无法登录",
        "description": "点击登录按钮无响应",
        "category_id": 1,
    }
    r = await client.post("/api/v1/tickets", json=body)
    assert r.status_code == 401
    assert r.json()["detail"] == "Not authenticated"


# API-TICKET-003: 标题超过 200 字符 422
async def test_create_ticket_title_too_long_422(client, customer_auth_headers, db):
    body = {"title": "x" * 201, "description": "desc", "category_id": 1}
    r = await client.post(
        "/api/v1/tickets", headers=customer_auth_headers, json=body
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert any(
        err["loc"] == ["body", "title"] and "String should have at most 200 characters" in err["msg"]
        for err in detail
    )


# API-TICKET-005: 查询不存在工单 404
async def test_get_ticket_not_found_404(client, customer_auth_headers, db):
    r = await client.get("/api/v1/tickets/99999", headers=customer_auth_headers)
    assert r.status_code == 404
    assert r.json()["detail"] == "工单不存在"


# API-TICKET-006: 客户越权查看他人工单 403
async def test_customer_access_other_ticket_403(
    client, customer_auth_headers, another_customer_ticket, db
):
    r = await client.get(
        f"/api/v1/tickets/{another_customer_ticket.id}",
        headers=customer_auth_headers,
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "无权访问该工单"


# API-TICKET-007: 客服可查看 open 工单
async def test_agent_view_open_ticket(client, agent_auth_headers, open_ticket, db):
    r = await client.get(
        f"/api/v1/tickets/{open_ticket.id}", headers=agent_auth_headers
    )
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == open_ticket.id
    assert data["status"] == "open"


# API-TICKET-008: 客服不可查看非分配 closed 工单
async def test_agent_view_closed_ticket_forbidden_403(
    client, agent_auth_headers, closed_ticket_assigned_to_other, db
):
    r = await client.get(
        f"/api/v1/tickets/{closed_ticket_assigned_to_other.id}",
        headers=agent_auth_headers,
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "无权访问该工单"
