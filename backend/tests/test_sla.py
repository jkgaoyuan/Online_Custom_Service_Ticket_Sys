import pytest
from datetime import datetime, timedelta
from sqlalchemy import select

from app.models.sla_record import SLARecord
from app.models.ticket import Ticket
from app.models.user import User
from app.models.category import Category
from app.schemas.ticket_reply import ReplyCreate
from app.services.reply_service import create_reply
from app.services.ticket_service import transition_ticket_status
from tests.conftest import _create_user, _create_category, _create_ticket


# API-SLA-101: SLARecord model can be created and persisted
async def test_sla_record_model(db):
    customer = await _create_user(db, "sla_customer", "customer")
    category = await _create_category(db)
    # Create ticket directly to avoid auto-SLA creation from service layer
    ticket = Ticket(
        ticket_no="TK-101",
        title="SLA ticket",
        description="Need help",
        category_id=category.id,
        requester_id=customer.id,
        priority="P2",
        source="web",
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    now = datetime.utcnow()
    sla = SLARecord(
        ticket_id=ticket.id,
        priority="P2",
        first_resp_hours=4,
        resolution_hours=24,
        first_resp_due=now + timedelta(hours=4),
        resolution_due=now + timedelta(hours=24),
        first_resp_at=None,
        resolved_at=None,
        first_resp_breached=False,
        resolution_breached=False,
        first_resp_warned_agent_3h=False,
        first_resp_warned_agent_2h=False,
        first_resp_warned_supervisor_1h=False,
        resolution_warned_agent_3h=False,
        resolution_warned_agent_2h=False,
        resolution_warned_supervisor_1h=False,
    )
    db.add(sla)
    await db.commit()
    await db.refresh(sla)

    assert sla.id is not None
    assert sla.ticket_id == ticket.id
    assert sla.priority == "P2"
    assert sla.first_resp_hours == 4
    assert sla.resolution_hours == 24
    assert sla.first_resp_due is not None
    assert sla.resolution_due is not None
    assert sla.first_resp_at is None
    assert sla.resolved_at is None
    assert sla.first_resp_breached is False
    assert sla.resolution_breached is False
    assert sla.first_resp_warned_agent_3h is False
    assert sla.first_resp_warned_agent_2h is False
    assert sla.first_resp_warned_supervisor_1h is False
    assert sla.resolution_warned_agent_3h is False
    assert sla.resolution_warned_agent_2h is False
    assert sla.resolution_warned_supervisor_1h is False

    # Verify relationship to ticket
    assert sla.ticket is not None
    assert sla.ticket.id == ticket.id

    # Verify we can query it back from DB
    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    db_sla = result.scalar_one_or_none()
    assert db_sla is not None
    assert db_sla.priority == "P2"


# API-SLA-201: create_ticket auto-creates SLA using category nested config
async def test_create_ticket_auto_creates_sla(db):
    customer = await _create_user(db, "auto_sla_customer", "customer")
    category = Category(
        name="Network",
        code="net",
        sla_config={
            "P0": {"first_resp_hours": 1, "resolution_hours": 4},
            "P1": {"first_resp_hours": 4, "resolution_hours": 24},
            "P2": {"first_resp_hours": 8, "resolution_hours": 48},
            "P3": {"first_resp_hours": 24, "resolution_hours": 72},
        },
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)

    ticket = await _create_ticket(
        db, "Auto SLA", "Desc", category.id, customer.id, priority="P1"
    )

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one_or_none()
    assert sla is not None
    assert sla.priority == "P1"
    assert sla.first_resp_hours == 4
    assert sla.resolution_hours == 24
    assert sla.first_resp_due is not None
    assert sla.resolution_due is not None


# API-SLA-202: empty category sla_config falls back to DEFAULT_SLA
async def test_create_ticket_uses_default_sla_when_category_empty(db):
    customer = await _create_user(db, "default_sla_customer", "customer")
    category = Category(name="Empty", code="empty", sla_config={})
    db.add(category)
    await db.commit()
    await db.refresh(category)

    ticket = await _create_ticket(
        db, "Default SLA", "Desc", category.id, customer.id, priority="P0"
    )

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one_or_none()
    assert sla is not None
    assert sla.first_resp_hours == 1
    assert sla.resolution_hours == 4


# API-SLA-203: old flat sla_config format is compatible
async def test_create_ticket_compat_flat_sla_config(db):
    customer = await _create_user(db, "compat_sla_customer", "customer")
    category = Category(
        name="Legacy",
        code="legacy",
        sla_config={"first_resp_hours": 2, "resolution_hours": 12},
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)

    ticket = await _create_ticket(
        db, "Compat SLA", "Desc", category.id, customer.id, priority="P2"
    )

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one_or_none()
    assert sla is not None
    assert sla.first_resp_hours == 2
    assert sla.resolution_hours == 12


# API-SLA-204: agent non-internal reply sets first_resp_at
async def test_agent_reply_sets_first_resp_at(db):
    customer = await _create_user(db, "fr_customer", "customer")
    agent = await _create_user(db, "fr_agent", "agent")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "FR Ticket", "Desc", category.id, customer.id)

    data = ReplyCreate(content="Agent reply", is_internal=False)
    await create_reply(db, ticket, data, agent.id, is_agent_reply=True)

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one_or_none()
    assert sla is not None
    assert sla.first_resp_at is not None


# API-SLA-205: internal reply does not set first_resp_at
async def test_internal_reply_does_not_set_first_resp_at(db):
    customer = await _create_user(db, "int_customer", "customer")
    agent = await _create_user(db, "int_agent", "agent")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "INT Ticket", "Desc", category.id, customer.id)

    data = ReplyCreate(content="Internal note", is_internal=True)
    await create_reply(db, ticket, data, agent.id, is_agent_reply=False)

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one_or_none()
    assert sla is not None
    assert sla.first_resp_at is None


# API-SLA-206: transition to resolved sets resolved_at on ticket and SLA
async def test_transition_to_resolved_sets_resolved_at(db):
    customer = await _create_user(db, "res_customer", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Res Ticket", "Desc", category.id, customer.id, status="in_progress"
    )

    ticket = await transition_ticket_status(db, ticket, "resolved")

    assert ticket.resolved_at is not None

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one_or_none()
    assert sla is not None
    assert sla.resolved_at is not None


# API-SLA-207: reopen (resolved -> in_progress) clears resolved_at
async def test_reopen_clears_resolved_at(db):
    customer = await _create_user(db, "reopen_customer", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Reopen Ticket", "Desc", category.id, customer.id, status="in_progress"
    )

    ticket = await transition_ticket_status(db, ticket, "resolved")
    assert ticket.resolved_at is not None

    ticket = await transition_ticket_status(db, ticket, "in_progress")
    assert ticket.resolved_at is None

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one_or_none()
    assert sla is not None
    assert sla.resolved_at is None


# ===== Task 5: SLA Query API and Embedding =====

# API-SLA-301: GET /api/v1/tickets/{id}/sla returns 200 with correct fields
async def test_api_get_ticket_sla(client, customer_auth_headers, db):
    customer = await _create_user(db, "sla_api_customer", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "SLA API Ticket", "Desc", category.id, customer.id)

    # Get token for the ticket owner
    from app.services.auth_service import create_access_token
    token = await create_access_token(customer.id)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get(f"/api/v1/tickets/{ticket.id}/sla", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["ticket_id"] == ticket.id
    assert data["priority"] == "P2"
    assert "first_resp_hours" in data
    assert "resolution_hours" in data
    assert "first_resp_due" in data
    assert "resolution_due" in data
    assert "first_resp_breached" in data
    assert "resolution_breached" in data


# API-SLA-302: customer cannot access another customer's ticket SLA (403)
async def test_api_get_ticket_sla_forbidden(client, customer_auth_headers, db):
    another_customer = await _create_user(db, "another_sla_customer", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "Private SLA", "Desc", category.id, another_customer.id)

    r = await client.get(f"/api/v1/tickets/{ticket.id}/sla", headers=customer_auth_headers)
    assert r.status_code == 403
    assert r.json()["detail"] == "无权访问该工单"


# API-SLA-303: admin GET /api/v1/admin/sla/overdue returns breached SLAs
async def test_api_admin_overdue_list(client, admin_auth_headers, db):
    customer = await _create_user(db, "overdue_customer", "customer")
    category = await _create_category(db)
    ticket1 = await _create_ticket(db, "Overdue 1", "Desc", category.id, customer.id)
    ticket2 = await _create_ticket(db, "Overdue 2", "Desc", category.id, customer.id)
    ticket3 = await _create_ticket(db, "Normal 3", "Desc", category.id, customer.id)

    # Manually mark SLAs as breached
    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket1.id))
    sla1 = result.scalar_one()
    sla1.first_resp_breached = True

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket2.id))
    sla2 = result.scalar_one()
    sla2.resolution_breached = True

    await db.commit()

    r = await client.get("/api/v1/admin/sla/overdue", headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 2
    ticket_ids = [item["ticket_id"] for item in data]
    assert ticket1.id in ticket_ids
    assert ticket2.id in ticket_ids
    assert ticket3.id not in ticket_ids

    # Filter by first_resp
    r = await client.get("/api/v1/admin/sla/overdue?breach_type=first_resp", headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert all(item["first_resp_breached"] for item in data)

    # Filter by resolution
    r = await client.get("/api/v1/admin/sla/overdue?breach_type=resolution", headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert all(item["resolution_breached"] for item in data)


# API-SLA-304: GET /api/v1/tickets/{id} includes sla field
async def test_ticket_detail_includes_sla_summary(client, customer_auth_headers, db):
    customer = await _create_user(db, "detail_sla_customer", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(db, "Detail SLA", "Desc", category.id, customer.id)

    # Get token for the ticket owner
    from app.services.auth_service import create_access_token
    token = await create_access_token(customer.id)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get(f"/api/v1/tickets/{ticket.id}", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "sla" in data
    assert data["sla"] is not None
    assert "first_resp_due" in data["sla"]
    assert "resolution_due" in data["sla"]
    assert "first_resp_breached" in data["sla"]
    assert "resolution_breached" in data["sla"]
    # SLASummary should NOT include ticket_id or hours
    assert "ticket_id" not in data["sla"]
    assert "first_resp_hours" not in data["sla"]


# API-SLA-208: closed ticket retains SLA record with resolved_at
async def test_closed_ticket_sla_exists(db):
    customer = await _create_user(db, "closed_customer", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Closed Ticket", "Desc", category.id, customer.id, status="in_progress"
    )

    ticket = await transition_ticket_status(db, ticket, "resolved")
    assert ticket.resolved_at is not None

    ticket = await transition_ticket_status(db, ticket, "closed")
    assert ticket.closed_at is not None

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one_or_none()
    assert sla is not None
    assert sla.resolved_at is not None

