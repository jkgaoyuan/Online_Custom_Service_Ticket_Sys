import pytest
from datetime import datetime, timedelta
from sqlalchemy import select

from app.models.sla_record import SLARecord
from app.models.ticket import Ticket
from app.models.user import User
from app.models.category import Category
from tests.conftest import _create_user, _create_category, _create_ticket


# API-SLA-101: SLARecord model can be created and persisted
async def test_sla_record_model(db):
    customer = await _create_user(db, "sla_customer", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "SLA ticket", "Need help", category.id, customer.id
    )

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
