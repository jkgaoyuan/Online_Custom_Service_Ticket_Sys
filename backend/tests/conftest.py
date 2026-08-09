from contextlib import asynccontextmanager
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, Base, engine
from app.main import app
from app.models.agent_skill import AgentSkill
from app.models.category import Category
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate
from app.services.auth_service import create_access_token
from app.services.ticket_service import create_ticket
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
        await db.commit()
        await db.refresh(ticket)
    return ticket


async def _create_resolved_ticket(
    db, title, description, category_id, requester_id, assignee_id=None, satisfaction=None
):
    ticket = await _create_ticket(
        db, title, description, category_id, requester_id,
        status="resolved", assignee_id=assignee_id
    )
    ticket.resolved_at = datetime.utcnow()
    ticket.satisfaction = satisfaction
    await db.commit()
    await db.refresh(ticket)
    return ticket


@pytest.fixture
async def another_customer_ticket(db):
    another_customer = await _create_user(db, "another_customer", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Another ticket", "Desc", category.id, another_customer.id
    )
    return ticket


@pytest.fixture
async def open_ticket(db):
    some_customer = await _create_user(db, "some_customer", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Open ticket", "Desc", category.id, some_customer.id, status="open"
    )
    return ticket


@pytest.fixture
async def closed_ticket_assigned_to_other(db):
    another_agent = await _create_user(db, "another_agent", "agent")
    some_customer = await _create_user(db, "some_customer2", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db,
        "Closed ticket",
        "Desc",
        category.id,
        some_customer.id,
        status="closed",
        assignee_id=another_agent.id,
    )
    return ticket
