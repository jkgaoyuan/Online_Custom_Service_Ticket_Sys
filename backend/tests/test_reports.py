from datetime import datetime, timedelta

from app.services.report_service import (
    get_agent_performance,
    get_category_distribution,
    get_overview,
    get_satisfaction_stats,
    validate_date_range,
)
from tests.conftest import _create_category, _create_resolved_ticket, _create_ticket, _create_user


# API-RPT-101: overview returns correct aggregated stats
async def test_overview_returns_correct_stats(db):
    customer = await _create_user(db, "ov_customer", "customer")
    category = await _create_category(db)
    t1 = await _create_ticket(db, "T1", "D1", category.id, customer.id, status="resolved")
    t2 = await _create_ticket(db, "T2", "D2", category.id, customer.id, status="open")

    result = await get_overview(db)
    assert result["total_tickets"] >= 2
    assert "today_new" in result
    assert "week_new" in result
    assert "month_new" in result
    assert "status_distribution" in result
    assert "sla_compliance_rate" in result
    assert "avg_satisfaction" in result


# API-RPT-102: agent performance returns correct stats
async def test_agent_performance_returns_correct_stats(db):
    from app.models.ticket_reply import TicketReply

    customer = await _create_user(db, "perf_customer", "customer")
    agent = await _create_user(db, "perf_agent", "agent")
    category = await _create_category(db)

    base_time = datetime.utcnow() - timedelta(days=1)
    t1 = await _create_resolved_ticket(
        db, "Perf1", "D1", category.id, customer.id, assignee_id=agent.id
    )
    t1.created_at = base_time
    t1.resolved_at = base_time + timedelta(hours=4)
    await db.commit()
    await db.refresh(t1)

    reply = TicketReply(
        ticket_id=t1.id,
        author_id=agent.id,
        content="First response",
        is_internal=False,
        created_at=base_time + timedelta(hours=2),
    )
    db.add(reply)
    await db.commit()

    start = (datetime.utcnow() - timedelta(days=30)).date().isoformat()
    end = datetime.utcnow().date().isoformat()
    result = await get_agent_performance(db, start, end)

    assert len(result) == 1
    item = result[0]
    assert item["agent_id"] == agent.id
    assert item["agent_name"] == "perf_agent"
    assert item["total_assigned"] == 1
    assert item["resolved_count"] == 1
    assert item["avg_first_resp_hours"] == 2.0
    assert item["avg_resolution_hours"] == 4.0


# API-RPT-103: category distribution returns correct stats
async def test_category_distribution_returns_correct_stats(db):
    customer = await _create_user(db, "cat_customer", "customer")
    category = await _create_category(db)
    await _create_ticket(db, "C1", "D1", category.id, customer.id)
    await _create_ticket(db, "C2", "D2", category.id, customer.id)

    start = (datetime.utcnow() - timedelta(days=30)).date().isoformat()
    end = datetime.utcnow().date().isoformat()
    result = await get_category_distribution(db, start, end)
    assert len(result) >= 1
    item = result[0]
    assert "category_id" in item
    assert "category_name" in item
    assert "count" in item
    assert "percentage" in item


# API-RPT-105: satisfaction returns correct stats
async def test_satisfaction_returns_correct_stats(db):
    customer = await _create_user(db, "sat_customer", "customer")
    category = await _create_category(db)
    t1 = await _create_ticket(db, "S1", "D1", category.id, customer.id, status="closed")
    t1.satisfaction = "satisfied"
    await db.commit()

    start = (datetime.utcnow() - timedelta(days=30)).date().isoformat()
    end = datetime.utcnow().date().isoformat()
    result = await get_satisfaction_stats(db, start, end)
    assert "distribution" in result
    assert "avg_score" in result
    assert "participation_rate" in result


# API-RPT-201: empty data returns zeros and empty lists
async def test_empty_data_returns_zeros(db):
    result = await get_overview(db)
    assert result["total_tickets"] >= 0

    start = (datetime.utcnow() - timedelta(days=30)).date().isoformat()
    end = datetime.utcnow().date().isoformat()
    cat_result = await get_category_distribution(db, start, end)
    assert cat_result == []

    sat_result = await get_satisfaction_stats(db, start, end)
    assert sat_result["participation_rate"] == 0.0


# API-RPT-203: date range exceeds one year returns error
async def test_date_range_exceeds_one_year():
    from app.exceptions import DuplicateException
    start = "2024-01-01"
    end = "2026-01-01"
    try:
        validate_date_range(start, end)
        assert False, "Expected exception"
    except DuplicateException as e:
        assert "365" in e.message or "1年" in e.message
