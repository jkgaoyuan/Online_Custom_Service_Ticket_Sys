from sqlalchemy import select

from app.models.category import Category
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate
from app.services.ticket_service import create_ticket
from app.utils.security import get_password_hash, verify_password


# === P0 正向 ===

# USR-001: admin 查询用户列表成功
async def test_admin_list_users_200(client, admin_auth_headers, db):
    r = await client.get("/api/v1/admin/users", headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "items" in data


# USR-002: 按 role=agent 筛选
async def test_list_users_filter_role_200(client, admin_auth_headers, db):
    r = await client.get("/api/v1/admin/users?role=agent", headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    for item in data["items"]:
        assert item["role"] == "agent"


# USR-003: 编辑用户信息成功
async def test_update_user_200(client, admin_auth_headers, db):
    user = User(username="testuser99", email="test99@test.com", password_hash=get_password_hash("p"), role="customer")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    body = {"username": "testuser99_new", "email": "new99@test.com", "is_active": False}
    r = await client.put(
        f"/api/v1/admin/users/{user.id}",
        headers=admin_auth_headers,
        json=body,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "testuser99_new"
    assert data["is_active"] is False


# USR-004: 重置密码成功
async def test_reset_password_200(client, admin_auth_headers, db):
    user = User(username="resetme", email="reset@test.com", password_hash=get_password_hash("old"), role="customer")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    r = await client.post(
        f"/api/v1/admin/users/{user.id}/reset-password",
        headers=admin_auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["temp_password"]) == 12

    # 验证密码已变更
    await db.refresh(user)
    assert verify_password(data["temp_password"], user.password_hash)


# USR-005: supervisor 只能查看 agent 列表
async def test_supervisor_list_agent_only_200(client, supervisor_auth_headers, db):
    r = await client.get("/api/v1/admin/users", headers=supervisor_auth_headers)
    assert r.status_code == 200
    data = r.json()
    for item in data["items"]:
        assert item["role"] == "agent"


# === P0 异常 ===

# USR-006: customer 访问用户列表 403
async def test_customer_list_users_403(client, customer_auth_headers, db):
    r = await client.get("/api/v1/admin/users", headers=customer_auth_headers)
    assert r.status_code == 403


# USR-007: 修改成已存在用户名 400
async def test_update_user_duplicate_username_400(client, admin_auth_headers, db):
    existing = User(username="existing_customer", email="existing@test.com", password_hash=get_password_hash("p"), role="customer")
    db.add(existing)
    await db.commit()
    await db.refresh(existing)

    user = User(username="dup_test", email="dup@test.com", password_hash=get_password_hash("p"), role="customer")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    body = {"username": existing.username}
    r = await client.put(
        f"/api/v1/admin/users/{user.id}",
        headers=admin_auth_headers,
        json=body,
    )
    assert r.status_code == 400
    assert "用户名已存在" in r.json()["detail"]


# USR-008: admin 修改自己的角色 400
async def test_admin_update_self_role_400(client, admin_auth_headers, db):
    admin = (await db.execute(select(User).where(User.username == "admin_test"))).scalar_one()
    body = {"role": "customer"}
    r = await client.put(
        f"/api/v1/admin/users/{admin.id}",
        headers=admin_auth_headers,
        json=body,
    )
    assert r.status_code == 400
    assert "不能修改自己的角色" in r.json()["detail"]


# === USR-009 ~ USR-014: 缺失测试补充 ===

# USR-009: get_user_detail 用户不存在返回 404
async def test_get_user_detail_not_found_404(client, admin_auth_headers, db):
    r = await client.get(
        "/api/v1/admin/users/999999",
        headers=admin_auth_headers,
    )
    assert r.status_code == 404
    assert "用户不存在" in r.json()["detail"]


# USR-010: get_user_detail supervisor 查看非 agent 用户 403
async def test_supervisor_get_user_detail_non_agent_403(client, supervisor_auth_headers, db):
    customer = User(
        username="detail_customer",
        email="detail_customer@test.com",
        password_hash=get_password_hash("p"),
        role="customer",
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    r = await client.get(
        f"/api/v1/admin/users/{customer.id}",
        headers=supervisor_auth_headers,
    )
    assert r.status_code == 403
    assert "无权查看该用户" in r.json()["detail"]


# USR-011: get_user_detail 返回 stats 统计
async def test_get_user_detail_stats_200(client, admin_auth_headers, db):
    agent = User(
        username="stats_agent",
        email="stats_agent@test.com",
        password_hash=get_password_hash("p"),
        role="agent",
    )
    db.add(agent)
    customer = User(
        username="stats_customer",
        email="stats_customer@test.com",
        password_hash=get_password_hash("p"),
        role="customer",
    )
    db.add(customer)
    await db.commit()
    await db.refresh(agent)
    await db.refresh(customer)

    category = Category(name="测试", code="test", default_priority="P2")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    open_data = TicketCreate(
        title="Open Ticket",
        description="Desc",
        category_id=category.id,
        priority="P2",
        source="web",
        assignee_id=agent.id,
    )
    open_ticket = await create_ticket(db, open_data, customer.id)

    resolved_data = TicketCreate(
        title="Resolved Ticket",
        description="Desc",
        category_id=category.id,
        priority="P2",
        source="web",
        assignee_id=agent.id,
    )
    resolved_ticket = await create_ticket(db, resolved_data, customer.id)
    resolved_ticket.status = "resolved"
    await db.commit()
    await db.refresh(resolved_ticket)

    r = await client.get(
        f"/api/v1/admin/users/{agent.id}",
        headers=admin_auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["stats"] is not None
    assert data["stats"]["total_tickets"] == 2
    assert data["stats"]["resolved_tickets"] == 1
    assert data["stats"]["open_tickets"] == 1


# USR-012: supervisor 修改非 agent 用户 403
async def test_supervisor_update_non_agent_403(client, supervisor_auth_headers, db):
    customer = User(
        username="upd_customer",
        email="upd_customer@test.com",
        password_hash=get_password_hash("p"),
        role="customer",
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    body = {"username": "should_fail"}
    r = await client.put(
        f"/api/v1/admin/users/{customer.id}",
        headers=supervisor_auth_headers,
        json=body,
    )
    assert r.status_code == 403
    assert "无权修改该用户" in r.json()["detail"]


# USR-013: supervisor 设置角色为非 agent 403
async def test_supervisor_update_role_to_non_agent_403(client, supervisor_auth_headers, db):
    agent = User(
        username="role_agent",
        email="role_agent@test.com",
        password_hash=get_password_hash("p"),
        role="agent",
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    body = {"role": "customer"}
    r = await client.put(
        f"/api/v1/admin/users/{agent.id}",
        headers=supervisor_auth_headers,
        json=body,
    )
    assert r.status_code == 403
    assert "只能设置角色为 agent" in r.json()["detail"]


# USR-014: get_user_detail 返回无 stats（customer 角色）
async def test_get_user_detail_customer_no_stats_200(client, admin_auth_headers, db):
    customer = User(
        username="no_stats_customer",
        email="no_stats_customer@test.com",
        password_hash=get_password_hash("p"),
        role="customer",
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    r = await client.get(
        f"/api/v1/admin/users/{customer.id}",
        headers=admin_auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["stats"] is None
