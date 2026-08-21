import pytest
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select

from app.models.ticket import Ticket
from app.models.user import User
from app.services.user_service import get_user_by_id, list_users, reset_user_password, update_user
from app.utils.security import get_password_hash

pytestmark = pytest.mark.anyio


class TestListUsers:
    async def test_list_all(self, db):
        u1 = User(username="u1", email="u1@example.com", password_hash=get_password_hash("p"), role="customer", is_active=True)
        u2 = User(username="u2", email="u2@example.com", password_hash=get_password_hash("p"), role="agent", is_active=True)
        db.add_all([u1, u2])
        await db.commit()

        result = await list_users(db)
        assert result["total"] >= 2
        assert len(result["items"]) >= 2

    async def test_filter_by_role(self, db):
        u1 = User(username="role_cust", email="rc@example.com", password_hash=get_password_hash("p"), role="customer", is_active=True)
        u2 = User(username="role_agent", email="ra@example.com", password_hash=get_password_hash("p"), role="agent", is_active=True)
        db.add_all([u1, u2])
        await db.commit()

        result = await list_users(db, role="agent")
        usernames = [item["username"] for item in result["items"]]
        assert "role_agent" in usernames
        assert "role_cust" not in usernames

    async def test_filter_by_is_active(self, db):
        active = User(username="active_u", email="au@example.com", password_hash=get_password_hash("p"), role="customer", is_active=True)
        inactive = User(username="inactive_u", email="iu@example.com", password_hash=get_password_hash("p"), role="customer", is_active=False)
        db.add_all([active, inactive])
        await db.commit()

        result = await list_users(db, is_active=False)
        usernames = [item["username"] for item in result["items"]]
        assert "inactive_u" in usernames
        assert "active_u" not in usernames

    async def test_pagination(self, db):
        users = [
            User(username=f"page_user{i}", email=f"p{i}@example.com", password_hash=get_password_hash("p"), role="customer", is_active=True)
            for i in range(5)
        ]
        db.add_all(users)
        await db.commit()

        result = await list_users(db, page=1, page_size=2)
        assert result["page"] == 1
        assert result["page_size"] == 2
        assert len(result["items"]) == 2
        assert result["total"] >= 5

    async def test_ticket_count_in_result(self, db):
        agent = User(username="stats_agent", email="sa@example.com", password_hash=get_password_hash("p"), role="agent", is_active=True)
        db.add(agent)
        await db.commit()
        await db.refresh(agent)

        # Use existing helper to create category and ticket safely
        from tests.conftest import _create_category, _create_ticket
        category = await _create_category(db)
        ticket = await _create_ticket(db, "Test", "Desc", category.id, agent.id, status="open", assignee_id=agent.id)
        await db.commit()

        result = await list_users(db, role="agent")
        agent_item = next((item for item in result["items"] if item["username"] == "stats_agent"), None)
        assert agent_item is not None
        assert agent_item["ticket_count"] == 1


class TestGetUserById:
    async def test_found(self, db):
        user = User(username="get_me", email="gm@example.com", password_hash=get_password_hash("p"), role="customer", is_active=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)

        result = await get_user_by_id(db, user.id)
        assert result is not None
        assert result.username == "get_me"

    async def test_not_found(self, db):
        result = await get_user_by_id(db, 99999)
        assert result is None


class TestUpdateUser:
    async def test_update_username(self, db):
        user = User(username="old_name", email="old@example.com", password_hash=get_password_hash("p"), role="customer", is_active=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)

        updated = await update_user(db, user.id, {"username": "new_name"})
        assert updated.username == "new_name"

    async def test_update_role(self, db):
        user = User(username="role_update", email="ru@example.com", password_hash=get_password_hash("p"), role="customer", is_active=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)

        updated = await update_user(db, user.id, {"role": "agent"})
        assert updated.role == "agent"

    async def test_invalid_role(self, db):
        user = User(username="bad_role", email="br@example.com", password_hash=get_password_hash("p"), role="customer", is_active=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)

        with pytest.raises(HTTPException, match="无效的角色"):
            await update_user(db, user.id, {"role": "hacker"})

    async def test_duplicate_username(self, db):
        u1 = User(username="existing", email="e1@example.com", password_hash=get_password_hash("p"), role="customer", is_active=True)
        u2 = User(username="updater", email="e2@example.com", password_hash=get_password_hash("p"), role="customer", is_active=True)
        db.add_all([u1, u2])
        await db.commit()
        await db.refresh(u2)

        with pytest.raises(HTTPException, match="用户名已存在"):
            await update_user(db, u2.id, {"username": "existing"})

    async def test_duplicate_email(self, db):
        u1 = User(username="u_email1", email="same_email@example.com", password_hash=get_password_hash("p"), role="customer", is_active=True)
        u2 = User(username="u_email2", email="other@example.com", password_hash=get_password_hash("p"), role="customer", is_active=True)
        db.add_all([u1, u2])
        await db.commit()
        await db.refresh(u2)

        with pytest.raises(HTTPException, match="邮箱已存在"):
            await update_user(db, u2.id, {"email": "same_email@example.com"})

    async def test_user_not_found(self, db):
        with pytest.raises(HTTPException, match="用户不存在"):
            await update_user(db, 99999, {"username": "x"})

    async def test_update_max_concurrent_tickets(self, db):
        user = User(username="max_tickets", email="mt@example.com", password_hash=get_password_hash("p"), role="agent", is_active=True, max_concurrent_tickets=5)
        db.add(user)
        await db.commit()
        await db.refresh(user)

        updated = await update_user(db, user.id, {"max_concurrent_tickets": 10})
        assert updated.max_concurrent_tickets == 10


class TestResetUserPassword:
    async def test_success(self, db):
        user = User(username="reset_me", email="rm@example.com", password_hash=get_password_hash("p"), role="customer", is_active=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)

        temp_pw = await reset_user_password(db, user.id)
        assert len(temp_pw) == 12

        # Verify password was actually changed
        await db.refresh(user)
        from app.utils.security import verify_password
        assert verify_password(temp_pw, user.password_hash) is True

        # Verify notification was created
        from app.models.notification import Notification
        result = await db.execute(select(Notification).where(Notification.user_id == user.id, Notification.type == "password_reset"))
        notif = result.scalar_one_or_none()
        assert notif is not None

    async def test_user_not_found(self, db):
        with pytest.raises(HTTPException, match="用户不存在"):
            await reset_user_password(db, 99999)
