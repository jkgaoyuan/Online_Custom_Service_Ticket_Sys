import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.exceptions import NotFoundException, ValidationException
from app.models.collaboration import TicketCollaboration
from app.services.collaboration_service import (
    get_collaborations,
    request_assistance,
    transfer_ticket,
)
from tests.conftest import _create_category, _create_ticket, _create_user

pytestmark = pytest.mark.anyio


class TestTransferTicket:
    async def test_transfer_success(self, db):
        agent = await _create_user(db, "agent_a", "agent")
        target = await _create_user(db, "agent_b", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Transfer me", "Desc", category.id, customer.id,
            status="open", assignee_id=agent.id
        )

        with patch(
            "app.services.collaboration_service.create_notification", new_callable=AsyncMock
        ) as mock_notif, patch(
            "app.services.collaboration_service.send_event", new_callable=AsyncMock
        ) as mock_send:
            result = await transfer_ticket(db, ticket.id, agent.id, target.id, "Handover")

        assert result.assignee_id == target.id
        assert result.status == "in_progress"
        mock_notif.assert_awaited_once()
        mock_send.assert_awaited_once()

    async def test_transfer_success_supervisor(self, db):
        supervisor = await _create_user(db, "supervisor", "supervisor")
        agent = await _create_user(db, "agent_a", "agent")
        target = await _create_user(db, "agent_b", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Transfer me", "Desc", category.id, customer.id,
            status="in_progress", assignee_id=agent.id
        )

        with patch(
            "app.services.collaboration_service.create_notification", new_callable=AsyncMock
        ), patch("app.services.collaboration_service.send_event", new_callable=AsyncMock):
            result = await transfer_ticket(db, ticket.id, supervisor.id, target.id, None)

        assert result.assignee_id == target.id

    async def test_transfer_success_admin(self, db):
        admin = await _create_user(db, "admin", "admin")
        agent = await _create_user(db, "agent_a", "agent")
        target = await _create_user(db, "agent_b", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Transfer me", "Desc", category.id, customer.id,
            status="in_progress", assignee_id=agent.id
        )

        with patch(
            "app.services.collaboration_service.create_notification", new_callable=AsyncMock
        ), patch("app.services.collaboration_service.send_event", new_callable=AsyncMock):
            result = await transfer_ticket(db, ticket.id, admin.id, target.id, None)

        assert result.assignee_id == target.id

    async def test_transfer_from_unassigned(self, db):
        supervisor = await _create_user(db, "supervisor", "supervisor")
        target = await _create_user(db, "target", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Unassigned", "Desc", category.id, customer.id,
            status="open", assignee_id=None
        )

        with patch(
            "app.services.collaboration_service.create_notification", new_callable=AsyncMock
        ) as mock_notif, patch(
            "app.services.collaboration_service.send_event", new_callable=AsyncMock
        ):
            result = await transfer_ticket(db, ticket.id, supervisor.id, target.id, "New assign")

        assert result.assignee_id == target.id
        assert result.status == "in_progress"
        assert "系统" in mock_notif.call_args.kwargs["message"]

    async def test_transfer_ticket_not_found(self, db):
        agent = await _create_user(db, "agent", "agent")
        target = await _create_user(db, "target", "agent")

        with pytest.raises(NotFoundException, match="工单不存在"):
            await transfer_ticket(db, 99999, agent.id, target.id, None)

    async def test_transfer_no_permission(self, db):
        assignee = await _create_user(db, "assignee", "agent")
        other_agent = await _create_user(db, "other", "agent")
        target = await _create_user(db, "target", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Transfer me", "Desc", category.id, customer.id,
            status="in_progress", assignee_id=assignee.id
        )

        with pytest.raises(ValidationException, match="只有当前处理人"):
            await transfer_ticket(db, ticket.id, other_agent.id, target.id, None)

    async def test_transfer_to_self(self, db):
        agent = await _create_user(db, "agent", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Transfer me", "Desc", category.id, customer.id,
            status="in_progress", assignee_id=agent.id
        )

        with pytest.raises(ValidationException, match="自己"):
            await transfer_ticket(db, ticket.id, agent.id, agent.id, None)

    async def test_transfer_target_not_agent(self, db):
        agent = await _create_user(db, "agent", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Transfer me", "Desc", category.id, customer.id,
            status="in_progress", assignee_id=agent.id
        )

        with pytest.raises(ValidationException, match="客服角色"):
            await transfer_ticket(db, ticket.id, agent.id, customer.id, None)

    async def test_transfer_target_nonexistent(self, db):
        agent = await _create_user(db, "agent", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Transfer me", "Desc", category.id, customer.id,
            status="in_progress", assignee_id=agent.id
        )

        with pytest.raises(ValidationException, match="客服角色"):
            await transfer_ticket(db, ticket.id, agent.id, 99999, None)

    async def test_transfer_target_inactive(self, db):
        agent = await _create_user(db, "agent", "agent")
        inactive = await _create_user(db, "inactive", "agent")
        inactive.is_active = False
        await db.commit()
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Transfer me", "Desc", category.id, customer.id,
            status="in_progress", assignee_id=agent.id
        )

        with pytest.raises(ValidationException, match="客服角色"):
            await transfer_ticket(db, ticket.id, agent.id, inactive.id, None)

    async def test_transfer_to_current_assignee(self, db):
        supervisor = await _create_user(db, "supervisor", "supervisor")
        agent = await _create_user(db, "agent", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Transfer me", "Desc", category.id, customer.id,
            status="in_progress", assignee_id=agent.id
        )

        with pytest.raises(ValidationException, match="当前处理人"):
            await transfer_ticket(db, ticket.id, supervisor.id, agent.id, None)

    async def test_transfer_reason_truncated(self, db):
        agent = await _create_user(db, "agent_a", "agent")
        target = await _create_user(db, "agent_b", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Transfer me", "Desc", category.id, customer.id,
            status="open", assignee_id=agent.id
        )

        with patch(
            "app.services.collaboration_service.create_notification", new_callable=AsyncMock
        ), patch("app.services.collaboration_service.send_event", new_callable=AsyncMock):
            result = await transfer_ticket(db, ticket.id, agent.id, target.id, "x" * 600)

        assert result.assignee_id == target.id
        from sqlalchemy import select

        collab_result = await db.execute(
            select(TicketCollaboration).where(
                TicketCollaboration.ticket_id == ticket.id,
                TicketCollaboration.type == "transfer",
            )
        )
        collab = collab_result.scalar_one()
        assert len(collab.reason) == 500


class TestRequestAssistance:
    async def test_request_assistance_success(self, db):
        agent = await _create_user(db, "agent", "agent")
        assist = await _create_user(db, "assist", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Assist", "Desc", category.id, customer.id,
            status="in_progress", assignee_id=agent.id
        )

        with patch(
            "app.services.collaboration_service.create_notification", new_callable=AsyncMock
        ) as mock_notif, patch(
            "app.services.collaboration_service.send_event", new_callable=AsyncMock
        ) as mock_send:
            result = await request_assistance(db, ticket.id, agent.id, assist.id, "Need help")

        assert result.type == "assist"
        assert result.to_user_id == assist.id
        assert result.from_user_id == agent.id
        mock_notif.assert_awaited_once()
        mock_send.assert_awaited_once()

    async def test_request_assistance_supervisor(self, db):
        supervisor = await _create_user(db, "supervisor", "supervisor")
        agent = await _create_user(db, "agent", "agent")
        assist = await _create_user(db, "assist", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Assist", "Desc", category.id, customer.id,
            status="in_progress", assignee_id=agent.id
        )

        with patch(
            "app.services.collaboration_service.create_notification", new_callable=AsyncMock
        ), patch("app.services.collaboration_service.send_event", new_callable=AsyncMock):
            result = await request_assistance(db, ticket.id, supervisor.id, assist.id, None)

        assert result.type == "assist"

    async def test_request_assistance_eager_load(self, db):
        agent = await _create_user(db, "agent", "agent")
        assist = await _create_user(db, "assist", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Assist", "Desc", category.id, customer.id,
            status="in_progress", assignee_id=agent.id
        )

        with patch(
            "app.services.collaboration_service.create_notification", new_callable=AsyncMock
        ), patch("app.services.collaboration_service.send_event", new_callable=AsyncMock):
            result = await request_assistance(db, ticket.id, agent.id, assist.id, "Help")

        assert result.from_user is not None
        assert result.from_user.id == agent.id
        assert result.to_user is not None
        assert result.to_user.id == assist.id

    async def test_request_assistance_ticket_not_found(self, db):
        agent = await _create_user(db, "agent", "agent")
        assist = await _create_user(db, "assist", "agent")

        with pytest.raises(NotFoundException, match="工单不存在"):
            await request_assistance(db, 99999, agent.id, assist.id, None)

    async def test_request_assistance_no_permission(self, db):
        assignee = await _create_user(db, "assignee", "agent")
        other_agent = await _create_user(db, "other", "agent")
        assist = await _create_user(db, "assist", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Assist", "Desc", category.id, customer.id,
            status="in_progress", assignee_id=assignee.id
        )

        with pytest.raises(ValidationException, match="只有当前处理人"):
            await request_assistance(db, ticket.id, other_agent.id, assist.id, None)

    async def test_request_assistance_to_self(self, db):
        agent = await _create_user(db, "agent", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Assist", "Desc", category.id, customer.id,
            status="in_progress", assignee_id=agent.id
        )

        with pytest.raises(ValidationException, match="自己"):
            await request_assistance(db, ticket.id, agent.id, agent.id, None)

    async def test_request_assistance_target_not_agent(self, db):
        agent = await _create_user(db, "agent", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Assist", "Desc", category.id, customer.id,
            status="in_progress", assignee_id=agent.id
        )

        with pytest.raises(ValidationException, match="客服角色"):
            await request_assistance(db, ticket.id, agent.id, customer.id, None)

    async def test_request_assistance_target_inactive(self, db):
        agent = await _create_user(db, "agent", "agent")
        inactive = await _create_user(db, "inactive", "agent")
        inactive.is_active = False
        await db.commit()
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Assist", "Desc", category.id, customer.id,
            status="in_progress", assignee_id=agent.id
        )

        with pytest.raises(ValidationException, match="客服角色"):
            await request_assistance(db, ticket.id, agent.id, inactive.id, None)

    async def test_request_assistance_duplicate(self, db):
        agent = await _create_user(db, "agent", "agent")
        assist = await _create_user(db, "assist", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Assist", "Desc", category.id, customer.id,
            status="in_progress", assignee_id=agent.id
        )

        with patch(
            "app.services.collaboration_service.create_notification", new_callable=AsyncMock
        ), patch("app.services.collaboration_service.send_event", new_callable=AsyncMock):
            await request_assistance(db, ticket.id, agent.id, assist.id, None)

        with pytest.raises(ValidationException, match="重复"):
            await request_assistance(db, ticket.id, agent.id, assist.id, None)


class TestGetCollaborations:
    async def test_get_collaborations_empty(self, db):
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Empty", "Desc", category.id, customer.id, status="open"
        )

        result = await get_collaborations(db, ticket.id)
        assert result == []

    async def test_get_collaborations_ordered_desc(self, db):
        agent = await _create_user(db, "agent", "agent")
        target = await _create_user(db, "target", "agent")
        customer = await _create_user(db, "customer", "customer")
        category = await _create_category(db)
        ticket = await _create_ticket(
            db, "Collab", "Desc", category.id, customer.id, status="open"
        )

        collab1 = TicketCollaboration(
            ticket_id=ticket.id,
            type="transfer",
            from_user_id=agent.id,
            to_user_id=target.id,
            reason="r1",
        )
        collab2 = TicketCollaboration(
            ticket_id=ticket.id,
            type="assist",
            from_user_id=agent.id,
            to_user_id=target.id,
            reason="r2",
        )
        db.add_all([collab1, collab2])
        await db.commit()

        # Ensure distinct timestamps for ordering
        collab1.created_at = datetime.utcnow() - timedelta(minutes=10)
        collab2.created_at = datetime.utcnow() - timedelta(minutes=5)
        await db.commit()

        result = await get_collaborations(db, ticket.id)
        assert len(result) == 2
        assert result[0].type == "assist"
        assert result[1].type == "transfer"
        assert result[0].from_user is not None
        assert result[0].to_user is not None
