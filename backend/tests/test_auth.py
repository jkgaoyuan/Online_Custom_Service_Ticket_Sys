from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.utils.security import get_password_hash


# ===== 辅助工厂函数 =====


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


async def _login(client: AsyncClient, username: str, password: str) -> str:
    r = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


def _auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


# ===== P0 正向 =====

# TC-USER-001: 正常登录
async def test_login_success_200(async_client, db):
    await _user(db, "agent01", role="agent", password="Pass1234")
    r = await async_client.post("/api/v1/auth/login", json={"username": "agent01", "password": "Pass1234"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "agent"


# TC-USER-002: 正常注册（客户）
async def test_register_customer_success_201(async_client, db):
    r = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "cust01", "email": "cust01@example.com", "password": "Pass1234"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["username"] == "cust01"
    assert data["role"] == "customer"


# TC-USER-003: 获取当前用户信息
async def test_me_success_200(async_client, db):
    user = await _user(db, "agent02", role="agent")
    token = await _login(async_client, "agent02", "Pass1234")
    r = await async_client.get("/api/v1/auth/me", headers=_auth_headers(token))
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "agent02"
    assert data["role"] == "agent"


# TC-USER-004: 管理员创建内部用户
async def test_admin_create_user_success_201(async_client, db):
    admin = await _user(db, "admin01", role="admin")
    token = await _login(async_client, "admin01", "Pass1234")
    r = await async_client.post(
        "/api/v1/auth/users",
        headers=_auth_headers(token),
        json={"username": "newagent", "email": "newagent@example.com", "password": "Pass1234", "role": "agent"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["role"] == "agent"


# ===== P0 异常 =====

# TC-USER-005: 登录密码错误
async def test_login_wrong_password_401(async_client, db):
    await _user(db, "agent03", role="agent", password="Pass1234")
    r = await async_client.post("/api/v1/auth/login", json={"username": "agent03", "password": "WrongPass"})
    assert r.status_code == 401
    assert "用户名或密码错误" in r.json()["detail"]


# TC-USER-006: 登录不存在的用户
async def test_login_nonexistent_user_401(async_client):
    r = await async_client.post("/api/v1/auth/login", json={"username": "nobody", "password": "Pass1234"})
    assert r.status_code == 401


# TC-USER-007: 访问 me 未认证
async def test_me_unauthorized_401(async_client):
    r = await async_client.get("/api/v1/auth/me")
    assert r.status_code == 401


# TC-USER-008: 注册重复用户名
async def test_register_duplicate_username_409(async_client, db):
    await _user(db, "dup01", email="a@example.com")
    r = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "dup01", "email": "b@example.com", "password": "Pass1234"},
    )
    assert r.status_code == 409


# TC-USER-009: 注册重复邮箱
async def test_register_duplicate_email_409(async_client, db):
    await _user(db, "dup02", email="dup@example.com")
    r = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "dup03", "email": "dup@example.com", "password": "Pass1234"},
    )
    assert r.status_code == 409


# TC-USER-010: 非管理员创建内部用户 403
async def test_nonadmin_create_user_403(async_client, db):
    user = await _user(db, "cust02", role="customer")
    token = await _login(async_client, "cust02", "Pass1234")
    r = await async_client.post(
        "/api/v1/auth/users",
        headers=_auth_headers(token),
        json={"username": "newagent2", "email": "newagent2@example.com", "password": "Pass1234", "role": "agent"},
    )
    assert r.status_code == 403


# ===== P1 边界 =====

# TC-USER-011: 密码强度不足（仅1种类别）
async def test_register_weak_password_422(async_client):
    r = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "weak01", "email": "weak01@example.com", "password": "password"},
    )
    assert r.status_code == 422


# TC-USER-012: 密码长度过短
async def test_register_short_password_422(async_client):
    r = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "weak02", "email": "weak02@example.com", "password": "P1!"},
    )
    assert r.status_code == 422


# TC-USER-013: 用户名过短
async def test_register_short_username_422(async_client):
    r = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "ab", "email": "ab@example.com", "password": "Pass1234"},
    )
    assert r.status_code == 422


# TC-USER-014: 禁用用户登录失败
async def test_login_inactive_user_401(async_client, db):
    await _user(db, "inactive01", is_active=False)
    r = await async_client.post("/api/v1/auth/login", json={"username": "inactive01", "password": "Pass1234"})
    assert r.status_code == 401


# ===== P1 权限 =====

# TC-USER-015: 主管创建内部用户（主管权限是否足够？按需求：仅 admin 可创建）
async def test_supervisor_create_user_403(async_client, db):
    user = await _user(db, "super01", role="supervisor")
    token = await _login(async_client, "super01", "Pass1234")
    r = await async_client.post(
        "/api/v1/auth/users",
        headers=_auth_headers(token),
        json={"username": "newagent3", "email": "newagent3@example.com", "password": "Pass1234", "role": "agent"},
    )
    assert r.status_code == 403


# ===== P1 安全 =====

# TC-USER-016: 伪造 Token 401
async def test_me_invalid_token_401(async_client):
    r = await async_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer fake-token"})
    assert r.status_code == 401


# TC-USER-017: SQL 注入用户名注册失败（被 schema 校验拦截或正常处理）
async def test_register_sql_injection_username_422(async_client):
    r = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "'; DROP TABLE users; --", "email": "sql@example.com", "password": "Pass1234"},
    )
    assert r.status_code == 422
