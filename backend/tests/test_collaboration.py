from sqlalchemy import select

from app.models.collaboration import TicketCollaboration
from app.models.notification import Notification
from app.models.ticket import Ticket
from app.models.user import User
from tests.conftest import _create_category, _create_ticket, _create_user


# === P0 正向测试 ===

# API-COLLAB-001: Agent successfully transfers own assigned ticket to another agent
async def test_api_collab_001_agent_transfer_success(client, agent_auth_headers, db):
    agent = (await db.execute(select(User).where(User.username == "agent_test"))).scalar_one()
    target_agent = await _create_user(db, "target_agent_001", "agent")
    customer = await _create_user(db, "customer_001", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Transfer test", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )
    body = {"to_user_id": target_agent.id, "reason": "Workload balance"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 201
    data = r.json()
    assert data["assignee_id"] == target_agent.id


# API-COLLAB-002: Agent successfully requests assistance from another agent
async def test_api_collab_002_agent_assist_success(client, agent_auth_headers, db):
    agent = (await db.execute(select(User).where(User.username == "agent_test"))).scalar_one()
    assist_agent = await _create_user(db, "assist_agent_002", "agent")
    customer = await _create_user(db, "customer_002", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Assist test", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )
    body = {"to_user_id": assist_agent.id, "reason": "Need expertise"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/assist", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 201
    data = r.json()
    assert data["type"] == "assist"
    assert data["to_user"]["id"] == assist_agent.id


# API-COLLAB-003: Get collaboration history returns list with transfer and assist records
async def test_api_collab_003_get_collaborations_list(client, agent_auth_headers, db):
    agent = (await db.execute(select(User).where(User.username == "agent_test"))).scalar_one()
    agent_a = await _create_user(db, "agent_a_003", "agent")
    agent_b = await _create_user(db, "agent_b_003", "agent")
    customer = await _create_user(db, "customer_003", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Collab list", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )
    # Assist first
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/assist",
        headers=agent_auth_headers,
        json={"to_user_id": agent_a.id, "reason": "Assist"},
    )
    assert r.status_code == 201
    # Then transfer
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=agent_auth_headers,
        json={"to_user_id": agent_b.id, "reason": "Transfer"},
    )
    assert r.status_code == 201
    # Get collaborations
    r = await client.get(
        f"/api/v1/tickets/{ticket.id}/collaborations", headers=agent_auth_headers
    )
    assert r.status_code == 200
    data = r.json()
    types = [c["type"] for c in data]
    assert "assist" in types
    assert "transfer" in types


# API-COLLAB-004: Supervisor can transfer any ticket
async def test_api_collab_004_supervisor_transfer_any_ticket(client, supervisor_auth_headers, db):
    another_agent = await _create_user(db, "another_agent_004", "agent")
    target_agent = await _create_user(db, "target_agent_004", "agent")
    customer = await _create_user(db, "customer_004", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Supervisor transfer", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=another_agent.id
    )
    body = {"to_user_id": target_agent.id, "reason": "Reassign"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer", headers=supervisor_auth_headers, json=body
    )
    assert r.status_code == 201
    data = r.json()
    assert data["assignee_id"] == target_agent.id


# API-COLLAB-005: Admin can transfer any ticket
async def test_api_collab_005_admin_transfer_any_ticket(client, admin_auth_headers, db):
    another_agent = await _create_user(db, "another_agent_005", "agent")
    target_agent = await _create_user(db, "target_agent_005", "agent")
    customer = await _create_user(db, "customer_005", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Admin transfer", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=another_agent.id
    )
    body = {"to_user_id": target_agent.id, "reason": "Reassign"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer", headers=admin_auth_headers, json=body
    )
    assert r.status_code == 201
    data = r.json()
    assert data["assignee_id"] == target_agent.id


# === 边界值/异常测试 ===

# API-COLLAB-006: Transfer by non-assignee agent returns 403
async def test_api_collab_006_non_assignee_agent_forbidden_403(client, agent_auth_headers, db):
    other_agent = await _create_user(db, "other_agent_006", "agent")
    customer = await _create_user(db, "customer_006", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Non assignee", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=other_agent.id
    )
    body = {"to_user_id": other_agent.id}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 403
    detail = r.json()["detail"]
    assert "只有当前处理人" in detail or "无权" in detail


# API-COLLAB-007: Customer cannot transfer/assist (403)
async def test_api_collab_007_customer_transfer_assist_forbidden_403(client, customer_auth_headers, db):
    customer = (await db.execute(select(User).where(User.username == "customer_test"))).scalar_one()
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Customer collab", "Desc", category.id, customer.id, status="open"
    )
    # Transfer
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=customer_auth_headers,
        json={"to_user_id": 1},
    )
    assert r.status_code == 403
    assert "需要角色" in r.json()["detail"]
    # Assist
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/assist",
        headers=customer_auth_headers,
        json={"to_user_id": 1},
    )
    assert r.status_code == 403
    assert "需要角色" in r.json()["detail"]


# API-COLLAB-008: Transfer to self returns 400 (ValidationException)
async def test_api_collab_008_transfer_to_self_400(client, agent_auth_headers, db):
    agent = (await db.execute(select(User).where(User.username == "agent_test"))).scalar_one()
    customer = await _create_user(db, "customer_008", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Self transfer", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )
    body = {"to_user_id": agent.id}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 422
    assert "自己" in r.json()["detail"]


# API-COLLAB-009: Assist to self returns 400
async def test_api_collab_009_assist_to_self_400(client, agent_auth_headers, db):
    agent = (await db.execute(select(User).where(User.username == "agent_test"))).scalar_one()
    customer = await _create_user(db, "customer_009", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Self assist", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )
    body = {"to_user_id": agent.id}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/assist", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 422
    assert "自己" in r.json()["detail"]


# API-COLLAB-010: Transfer to non-existent user returns 400
async def test_api_collab_010_transfer_to_nonexistent_user_400(client, agent_auth_headers, db):
    agent = (await db.execute(select(User).where(User.username == "agent_test"))).scalar_one()
    customer = await _create_user(db, "customer_010", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Nonexistent user", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )
    body = {"to_user_id": 99999}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "目标" in detail or "有效" in detail


# API-COLLAB-011: Transfer to inactive user returns 400
async def test_api_collab_011_transfer_to_inactive_user_400(client, agent_auth_headers, db):
    agent = (await db.execute(select(User).where(User.username == "agent_test"))).scalar_one()
    inactive_agent = await _create_user(db, "inactive_agent_011", "agent")
    inactive_agent.is_active = False
    await db.commit()
    customer = await _create_user(db, "customer_011", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Inactive user", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )
    body = {"to_user_id": inactive_agent.id}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 422
    assert "有效" in r.json()["detail"]


# API-COLLAB-012: Transfer to customer returns 400
async def test_api_collab_012_transfer_to_customer_400(client, agent_auth_headers, db):
    agent = (await db.execute(select(User).where(User.username == "agent_test"))).scalar_one()
    target_customer = await _create_user(db, "target_customer_012", "customer")
    customer = await _create_user(db, "customer_012", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Transfer to customer", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )
    body = {"to_user_id": target_customer.id}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "客服" in detail or "角色" in detail


# API-COLLAB-013: Duplicate assist request returns 400
async def test_api_collab_013_duplicate_assist_400(client, agent_auth_headers, db):
    agent = (await db.execute(select(User).where(User.username == "agent_test"))).scalar_one()
    assist_agent = await _create_user(db, "assist_agent_013", "agent")
    customer = await _create_user(db, "customer_013", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Duplicate assist", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )
    body = {"to_user_id": assist_agent.id}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/assist", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 201
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/assist", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "重复" in detail or "已" in detail


# API-COLLAB-014: Transfer non-existent ticket returns 404
async def test_api_collab_014_transfer_nonexistent_ticket_404(client, agent_auth_headers, db):
    body = {"to_user_id": 1}
    r = await client.post(
        "/api/v1/tickets/99999/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "工单不存在"


# API-COLLAB-015: Get collaborations for non-existent ticket returns 404
async def test_api_collab_015_get_collaborations_nonexistent_ticket_404(client, agent_auth_headers, db):
    r = await client.get(
        "/api/v1/tickets/99999/collaborations", headers=agent_auth_headers
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "工单不存在"


# === DB side-effect 验证 ===

# API-COLLAB-016: After transfer, notification created for target user
async def test_api_collab_016_transfer_notification_created(client, agent_auth_headers, db):
    agent = (await db.execute(select(User).where(User.username == "agent_test"))).scalar_one()
    target_agent = await _create_user(db, "target_agent_016", "agent")
    customer = await _create_user(db, "customer_016", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Transfer notify", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )
    body = {"to_user_id": target_agent.id, "reason": "Handover"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 201
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == target_agent.id,
            Notification.type == "ticket_transferred",
        )
    )
    notification = result.scalar_one_or_none()
    assert notification is not None
    assert "转交" in notification.title


# API-COLLAB-017: After assist, notification created for target user
async def test_api_collab_017_assist_notification_created(client, agent_auth_headers, db):
    agent = (await db.execute(select(User).where(User.username == "agent_test"))).scalar_one()
    assist_agent = await _create_user(db, "assist_agent_017", "agent")
    customer = await _create_user(db, "customer_017", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Assist notify", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )
    body = {"to_user_id": assist_agent.id, "reason": "Help needed"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/assist", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 201
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == assist_agent.id,
            Notification.type == "assistance_requested",
        )
    )
    notification = result.scalar_one_or_none()
    assert notification is not None
    assert "协助" in notification.title


# API-COLLAB-018: After transfer, ticket.assignee_id updated to new user
async def test_api_collab_018_transfer_updates_assignee_id(client, agent_auth_headers, db):
    agent = (await db.execute(select(User).where(User.username == "agent_test"))).scalar_one()
    target_agent = await _create_user(db, "target_agent_018", "agent")
    customer = await _create_user(db, "customer_018", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Update assignee", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )
    ticket_id = ticket.id
    body = {"to_user_id": target_agent.id}
    r = await client.post(
        f"/api/v1/tickets/{ticket_id}/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 201
    result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id).execution_options(populate_existing=True)
    )
    updated_ticket = result.scalar_one()
    assert updated_ticket.assignee_id == target_agent.id


# API-COLLAB-019: After transfer, ticket.status changed from open to in_progress
async def test_api_collab_019_transfer_open_to_in_progress(client, agent_auth_headers, db):
    agent = (await db.execute(select(User).where(User.username == "agent_test"))).scalar_one()
    target_agent = await _create_user(db, "target_agent_019", "agent")
    customer = await _create_user(db, "customer_019", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Status change", "Desc", category.id, customer.id,
        status="open", assignee_id=agent.id
    )
    ticket_id = ticket.id
    body = {"to_user_id": target_agent.id}
    r = await client.post(
        f"/api/v1/tickets/{ticket_id}/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 201
    result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id).execution_options(populate_existing=True)
    )
    updated_ticket = result.scalar_one()
    assert updated_ticket.status == "in_progress"


# API-COLLAB-020: Transfer reason truncated to 500 chars
async def test_api_collab_020_transfer_reason_truncated_500(client, agent_auth_headers, db):
    agent = (await db.execute(select(User).where(User.username == "agent_test"))).scalar_one()
    target_agent = await _create_user(db, "target_agent_020", "agent")
    customer = await _create_user(db, "customer_020", "customer")
    category = await _create_category(db)
    ticket = await _create_ticket(
        db, "Reason truncate", "Desc", category.id, customer.id,
        status="in_progress", assignee_id=agent.id
    )
    body = {"to_user_id": target_agent.id, "reason": "x" * 600}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 201
    result = await db.execute(
        select(TicketCollaboration).where(
            TicketCollaboration.ticket_id == ticket.id,
            TicketCollaboration.type == "transfer",
        )
    )
    collab = result.scalar_one_or_none()
    assert collab is not None
    assert len(collab.reason) == 500
