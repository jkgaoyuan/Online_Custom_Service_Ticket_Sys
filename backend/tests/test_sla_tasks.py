import pytest
from datetime import datetime, timedelta
from sqlalchemy import select

from app.models.notification import Notification
from app.models.sla_record import SLARecord
from app.tasks.sla_tasks import _scan_first_resp
from tests.conftest import _create_user, _create_category, _create_ticket


async def test_scan_first_resp_agent_3h_warning(db):
    customer = await _create_user(db, "cust_3h", "customer")
    agent = await _create_user(db, "agent_3h", "agent")
    supervisor = await _create_user(db, "super_3h", "supervisor")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "3h Warn", "Desc", category.id, customer.id, assignee_id=agent.id
    )

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one()

    now = datetime.utcnow()
    sla.first_resp_due = now + timedelta(hours=2.5)
    sla.first_resp_hours = 4
    await db.commit()

    await _scan_first_resp(db, now, [supervisor.id])
    await db.commit()

    result = await db.execute(select(SLARecord).where(SLARecord.id == sla.id))
    updated = result.scalar_one()
    assert updated.first_resp_warned_agent_3h is True

    result = await db.execute(
        select(Notification).where(
            Notification.user_id == agent.id,
            Notification.type == "sla_warning",
        )
    )
    notif = result.scalar_one_or_none()
    assert notif is not None
    assert "即将超时" in notif.title


async def test_scan_first_resp_supervisor_1h_warning(db):
    customer = await _create_user(db, "cust_1h", "customer")
    agent = await _create_user(db, "agent_1h", "agent")
    supervisor = await _create_user(db, "super_1h", "supervisor")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "1h Warn", "Desc", category.id, customer.id, assignee_id=agent.id
    )

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one()

    now = datetime.utcnow()
    sla.first_resp_due = now + timedelta(minutes=45)
    sla.first_resp_hours = 4
    sla.first_resp_warned_agent_3h = True
    sla.first_resp_warned_agent_2h = True
    await db.commit()

    await _scan_first_resp(db, now, [supervisor.id])
    await db.commit()

    result = await db.execute(select(SLARecord).where(SLARecord.id == sla.id))
    updated = result.scalar_one()
    assert updated.first_resp_warned_supervisor_1h is True

    # Supervisor SHOULD get it
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == supervisor.id,
            Notification.type == "sla_warning",
        )
    )
    notif = result.scalar_one_or_none()
    assert notif is not None
    assert "即将超时" in notif.title


async def test_scan_first_resp_breach(db):
    customer = await _create_user(db, "cust_breach", "customer")
    agent = await _create_user(db, "agent_breach", "agent")
    supervisor = await _create_user(db, "super_breach", "supervisor")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Breach", "Desc", category.id, customer.id, assignee_id=agent.id
    )

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one()

    now = datetime.utcnow()
    sla.first_resp_due = now - timedelta(hours=1)
    sla.first_resp_hours = 4
    await db.commit()

    await _scan_first_resp(db, now, [supervisor.id])
    await db.commit()

    result = await db.execute(select(SLARecord).where(SLARecord.id == sla.id))
    updated = result.scalar_one()
    assert updated.first_resp_breached is True

    # Both agent and supervisor should get breach notification
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == agent.id,
            Notification.type == "sla_breach",
        )
    )
    assert result.scalar_one_or_none() is not None

    result = await db.execute(
        select(Notification).where(
            Notification.user_id == supervisor.id,
            Notification.type == "sla_breach",
        )
    )
    assert result.scalar_one_or_none() is not None


async def test_short_sla_no_3h_warning(db):
    customer = await _create_user(db, "cust_short", "customer")
    agent = await _create_user(db, "agent_short", "agent")
    supervisor = await _create_user(db, "super_short", "supervisor")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Short", "Desc", category.id, customer.id, assignee_id=agent.id
    )

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one()

    now = datetime.utcnow()
    sla.first_resp_due = now + timedelta(minutes=30)
    sla.first_resp_hours = 1
    await db.commit()

    await _scan_first_resp(db, now, [supervisor.id])
    await db.commit()

    result = await db.execute(select(SLARecord).where(SLARecord.id == sla.id))
    updated = result.scalar_one()
    assert updated.first_resp_warned_agent_3h is False
    assert updated.first_resp_warned_agent_2h is False
    assert updated.first_resp_warned_supervisor_1h is False
    assert updated.first_resp_breached is False

    result = await db.execute(select(Notification))
    assert result.scalars().all() == []


async def test_scan_no_duplicate_notification(db):
    customer = await _create_user(db, "cust_dup", "customer")
    agent = await _create_user(db, "agent_dup", "agent")
    supervisor = await _create_user(db, "super_dup", "supervisor")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Dup", "Desc", category.id, customer.id, assignee_id=agent.id
    )

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one()

    now = datetime.utcnow()
    sla.first_resp_due = now + timedelta(hours=2.5)
    sla.first_resp_hours = 4
    await db.commit()

    # First scan
    await _scan_first_resp(db, now, [supervisor.id])
    await db.commit()

    # Second scan
    await _scan_first_resp(db, now, [supervisor.id])
    await db.commit()

    result = await db.execute(
        select(Notification).where(
            Notification.user_id == agent.id,
            Notification.type == "sla_warning",
        )
    )
    notifs = result.scalars().all()
    assert len(notifs) == 1
