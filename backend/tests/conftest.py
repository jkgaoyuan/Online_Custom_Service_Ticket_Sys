from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, Base, engine
from app.main import app
from app.models.user import User
from app.services.auth_service import create_access_token
from app.utils.security import get_password_hash


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


# 测试期间禁用 lifespan（避免默认管理员创建等副作用）
@asynccontextmanager
async def _noop_lifespan(app):
    yield


app.router.lifespan_context = _noop_lifespan


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def client(async_client):
    return async_client


# ===== 辅助工厂函数 =====


async def _create_user(
    db: AsyncSession,
    username: str,
    role: str = "customer",
    password: str = "Pass1234",
) -> User:
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


async def _auth_headers(
    db: AsyncSession,
    username: str,
    role: str,
    password: str = "Pass1234",
) -> dict:
    user = await _create_user(db, username, role, password)
    token = await create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_auth_headers(db):
    return await _auth_headers(db, "admin_test", "admin")


@pytest.fixture
async def supervisor_auth_headers(db):
    return await _auth_headers(db, "supervisor_test", "supervisor")


@pytest.fixture
async def agent_auth_headers(db):
    return await _auth_headers(db, "agent_test", "agent")


@pytest.fixture
async def customer_auth_headers(db):
    return await _auth_headers(db, "customer_test", "customer")
