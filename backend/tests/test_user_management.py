import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.utils.security import get_password_hash, verify_password


async def _user(
    db: AsyncSession,
    username: str,
    role: str = "customer",
    password: str = "Pass1234",
    email: str = None,
    is_active: bool = True,
) -> User:
    user = User(
        username=username,
        email=email or f"{username}@example.com",
        password_hash=get_password_hash(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# 1. Admin lists users with pagination
async def test_admin_list_users_200(async_client, db, admin_auth_headers):
    await _user(db, "agent01", role="agent")
    await _user(db, "cust01", role="customer")
    r = await async_client.get("/api/v1/admin/users", headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "items" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= 2


# 2. Filter by role=agent
async def test_list_users_filter_role_200(async_client, db, admin_auth_headers):
    await _user(db, "agent02", role="agent")
    await _user(db, "cust02", role="customer")
    r = await async_client.get("/api/v1/admin/users?role=agent", headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    for item in data["items"]:
        assert item["role"] == "agent"


# 3. Update user
async def test_update_user_200(async_client, db, admin_auth_headers):
    user = await _user(db, "updateme", role="agent")
    r = await async_client.put(
        f"/api/v1/admin/users/{user.id}",
        headers=admin_auth_headers,
        json={"username": "updated_name", "email": "updated@example.com", "is_active": False},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "updated_name"
    assert data["email"] == "updated@example.com"
    assert data["is_active"] is False


# 4. Reset password
async def test_reset_password_200(async_client, db, admin_auth_headers):
    user = await _user(db, "resetme", role="agent", password="OldPass1234")
    r = await async_client.post(
        f"/api/v1/admin/users/{user.id}/reset-password",
        headers=admin_auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "temp_password" in data
    assert len(data["temp_password"]) == 12

    # Verify login works with temp password
    login_r = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "resetme", "password": data["temp_password"]},
    )
    assert login_r.status_code == 200
    assert "access_token" in login_r.json()


# 5. Supervisor can only list agent users
async def test_supervisor_list_agent_only_200(async_client, db, supervisor_auth_headers):
    await _user(db, "agent03", role="agent")
    await _user(db, "cust03", role="customer")
    r = await async_client.get("/api/v1/admin/users", headers=supervisor_auth_headers)
    assert r.status_code == 200
    data = r.json()
    for item in data["items"]:
        assert item["role"] == "agent"


# 6. Customer cannot list users
async def test_customer_list_users_403(async_client, db, customer_auth_headers):
    r = await async_client.get("/api/v1/admin/users", headers=customer_auth_headers)
    assert r.status_code == 403


# 7. Duplicate username on update
async def test_update_user_duplicate_username_409(async_client, db, admin_auth_headers):
    user1 = await _user(db, "dupuser1", role="agent")
    user2 = await _user(db, "dupuser2", role="agent")
    r = await async_client.put(
        f"/api/v1/admin/users/{user2.id}",
        headers=admin_auth_headers,
        json={"username": "dupuser1"},
    )
    assert r.status_code == 409


# 8. Admin cannot change own role
async def test_admin_update_self_role_400(async_client, db, admin_auth_headers):
    from app.services.auth_service import get_user_by_username
    admin = await get_user_by_username(db, "admin_test")
    r = await async_client.put(
        f"/api/v1/admin/users/{admin.id}",
        headers=admin_auth_headers,
        json={"role": "customer"},
    )
    assert r.status_code == 400
