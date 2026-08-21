import pytest
from datetime import datetime
from jose import jwt
from sqlalchemy import select

from app.config import get_settings
from app.exceptions import DuplicateException
from app.models.user import User
from app.schemas.user import UserCreate, UserCreateInternal
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_default_admin,
    create_user_by_admin,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    list_active_users,
    register_user,
)
from app.utils.security import get_password_hash

pytestmark = pytest.mark.anyio


class TestGetUser:
    async def test_get_user_by_id(self, db):
        user = User(
            username="test_user",
            email="test@example.com",
            password_hash=get_password_hash("Pass1234"),
            role="customer",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        result = await get_user_by_id(db, user.id)
        assert result is not None
        assert result.username == "test_user"

    async def test_get_user_by_id_not_found(self, db):
        result = await get_user_by_id(db, 99999)
        assert result is None

    async def test_get_user_by_username(self, db):
        user = User(
            username="by_name",
            email="by_name@example.com",
            password_hash=get_password_hash("Pass1234"),
            role="customer",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        result = await get_user_by_username(db, "by_name")
        assert result is not None
        assert result.email == "by_name@example.com"

    async def test_get_user_by_email(self, db):
        user = User(
            username="by_email",
            email="by_email@example.com",
            password_hash=get_password_hash("Pass1234"),
            role="customer",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        result = await get_user_by_email(db, "by_email@example.com")
        assert result is not None
        assert result.username == "by_email"


class TestAuthenticateUser:
    async def test_success(self, db):
        user = User(
            username="auth_user",
            email="auth@example.com",
            password_hash=get_password_hash("CorrectPass1"),
            role="customer",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        result = await authenticate_user(db, "auth_user", "CorrectPass1")
        assert result is not None
        assert result.username == "auth_user"

    async def test_wrong_password(self, db):
        user = User(
            username="auth_user2",
            email="auth2@example.com",
            password_hash=get_password_hash("CorrectPass1"),
            role="customer",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        result = await authenticate_user(db, "auth_user2", "WrongPass")
        assert result is None

    async def test_user_not_found(self, db):
        result = await authenticate_user(db, "nonexistent", "anypass")
        assert result is None


class TestCreateAccessToken:
    async def test_token_contains_user_id(self):
        token = await create_access_token(42)
        settings = get_settings()
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "42"
        assert "exp" in payload


class TestRegisterUser:
    async def test_success(self, db):
        data = UserCreate(
            username="new_user",
            email="new@example.com",
            password="StrongPass1",
            role="customer",
        )
        user = await register_user(db, data)
        assert user.username == "new_user"
        assert user.email == "new@example.com"
        assert user.role == "customer"

    async def test_duplicate_username(self, db):
        data = UserCreate(
            username="dup_user",
            email="dup1@example.com",
            password="StrongPass1",
            role="customer",
        )
        await register_user(db, data)

        data2 = UserCreate(
            username="dup_user",
            email="dup2@example.com",
            password="StrongPass1",
            role="customer",
        )
        with pytest.raises(DuplicateException, match="用户名已存在"):
            await register_user(db, data2)

    async def test_duplicate_email(self, db):
        data = UserCreate(
            username="email_user1",
            email="same@example.com",
            password="StrongPass1",
            role="customer",
        )
        await register_user(db, data)

        data2 = UserCreate(
            username="email_user2",
            email="same@example.com",
            password="StrongPass1",
            role="customer",
        )
        with pytest.raises(DuplicateException, match="邮箱已存在"):
            await register_user(db, data2)


class TestCreateUserByAdmin:
    async def test_success(self, db):
        data = UserCreateInternal(
            username="admin_created",
            email="admin_created@example.com",
            password="StrongPass1",
            role="agent",
        )
        user = await create_user_by_admin(db, data)
        assert user.role == "agent"

    async def test_duplicate_username(self, db):
        data = UserCreateInternal(
            username="admin_dup",
            email="a1@example.com",
            password="StrongPass1",
            role="customer",
        )
        await create_user_by_admin(db, data)

        data2 = UserCreateInternal(
            username="admin_dup",
            email="a2@example.com",
            password="StrongPass1",
            role="customer",
        )
        with pytest.raises(DuplicateException, match="用户名已存在"):
            await create_user_by_admin(db, data2)


class TestListActiveUsers:
    async def test_list_all_active(self, db):
        user1 = User(username="active1", email="a1@example.com", password_hash=get_password_hash("p"), role="customer", is_active=True)
        user2 = User(username="active2", email="a2@example.com", password_hash=get_password_hash("p"), role="agent", is_active=True)
        inactive = User(username="inactive", email="i@example.com", password_hash=get_password_hash("p"), role="customer", is_active=False)
        db.add_all([user1, user2, inactive])
        await db.commit()

        result = await list_active_users(db)
        usernames = [u.username for u in result]
        assert "active1" in usernames
        assert "active2" in usernames
        assert "inactive" not in usernames

    async def test_filter_by_role(self, db):
        agent = User(username="agent_only", email="ag@example.com", password_hash=get_password_hash("p"), role="agent", is_active=True)
        customer = User(username="cust_only", email="cu@example.com", password_hash=get_password_hash("p"), role="customer", is_active=True)
        db.add_all([agent, customer])
        await db.commit()

        result = await list_active_users(db, role="agent")
        usernames = [u.username for u in result]
        assert "agent_only" in usernames
        assert "cust_only" not in usernames


class TestCreateDefaultAdmin:
    async def test_creates_admin_when_missing(self, db):
        await create_default_admin(db)
        result = await db.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()
        assert admin is not None
        assert admin.role == "admin"

    async def test_idempotent(self, db):
        await create_default_admin(db)
        await create_default_admin(db)
        result = await db.execute(select(User).where(User.username == "admin"))
        admins = result.scalars().all()
        assert len(admins) == 1
