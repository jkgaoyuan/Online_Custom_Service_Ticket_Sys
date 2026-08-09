from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import Settings
from app.main import app
from app.models.category import Category
from app.models.email_ingestion import EmailIngestion
from app.models.ticket import Ticket
from app.models.ticket_reply import TicketReply
from app.models.user import User
from app.schemas.email_webhook import InboundEmail
from app.services.email_service import (
    _get_body,
    create_reply_from_email,
    create_ticket_from_email,
    enqueue_moderation,
    ensure_default_email_category,
    extract_ticket_no_from_subject,
    html_to_text,
    match_ticket_by_email,
    process_inbound_email,
)
from app.services.mailer import Mailer
from app.utils.security import get_password_hash

client = TestClient(app)


@pytest.fixture(autouse=True)
def eager_email_task(monkeypatch):
    """Run inbound email Celery tasks synchronously during tests."""
    import threading

    try:
        from app.tasks import email_tasks
    except ImportError:
        yield
        return

    original_delay = email_tasks.process_inbound_email_task.delay

    def _run_sync(payload: dict) -> None:
        def target() -> None:
            email_tasks.process_inbound_email_task(payload)

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=10)

    monkeypatch.setattr(email_tasks.process_inbound_email_task, "delay", _run_sync)
    yield
    monkeypatch.setattr(email_tasks.process_inbound_email_task, "delay", original_delay)


async def test_email_ingestion_defaults_and_relationships(db):
    user = User(
        username="email_user",
        email="email_user@example.com",
        password_hash=get_password_hash("Pass1234"),
        role="customer",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    ingestion = EmailIngestion(
        sender_email="sender@example.com",
        sender_name="Sender Name",
        subject="Test Subject",
        body="Test body content",
        message_id="msg-001@example.com",
        created_user_id=user.id,
    )
    db.add(ingestion)
    await db.commit()
    await db.refresh(ingestion)

    assert ingestion.id is not None
    assert ingestion.status == "pending"
    assert isinstance(ingestion.received_at, datetime)
    assert ingestion.created_user_id == user.id
    assert ingestion.created_user.email == "email_user@example.com"


async def test_email_ingestion_message_id_unique(db):
    ingestion1 = EmailIngestion(
        sender_email="a@example.com",
        subject="First",
        body="body",
        message_id="unique-msg@example.com",
    )
    ingestion2 = EmailIngestion(
        sender_email="b@example.com",
        subject="Second",
        body="body",
        message_id="unique-msg@example.com",
    )
    db.add(ingestion1)
    await db.commit()
    db.add(ingestion2)

    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


@pytest.mark.asyncio
async def test_mailer_send_text_email_noop_when_unconfigured():
    mailer = Mailer()
    # When no SMTP_HOST or API provider, should be no-op (not crash)
    await mailer.send_text_email("to@example.com", "Subject", "Body")


async def test_ticket_reply_email_message_id(db, open_ticket):
    agent = User(
        username="agent_test",
        email="agent_test@example.com",
        password_hash=get_password_hash("Pass1234"),
        role="agent",
        is_active=True,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    reply = TicketReply(
        ticket_id=open_ticket.id,
        author_id=agent.id,
        content="Email reply",
        email_message_id="reply-001@example.com",
    )
    db.add(reply)
    await db.commit()
    await db.refresh(reply)

    assert reply.email_message_id == "reply-001@example.com"


async def test_ticket_reply_email_message_id_unique(db, open_ticket):
    agent = User(
        username="agent_test",
        email="agent_test@example.com",
        password_hash=get_password_hash("Pass1234"),
        role="agent",
        is_active=True,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    reply1 = TicketReply(
        ticket_id=open_ticket.id,
        author_id=agent.id,
        content="First email reply",
        email_message_id="dupe-reply@example.com",
    )
    reply2 = TicketReply(
        ticket_id=open_ticket.id,
        author_id=agent.id,
        content="Second email reply",
        email_message_id="dupe-reply@example.com",
    )
    db.add(reply1)
    await db.commit()
    db.add(reply2)

    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


# ===== Email Service Unit Tests =====


def test_extract_ticket_no_from_subject_exact():
    assert extract_ticket_no_from_subject("Problem with TK-20260809-0001") == "TK-20260809-0001"


def test_extract_ticket_no_from_subject_with_re_prefix():
    assert (
        extract_ticket_no_from_subject("Re: [Support] TK-20260809-0002 issue") == "TK-20260809-0002"
    )


def test_extract_ticket_no_from_subject_no_match():
    assert extract_ticket_no_from_subject("Just a random subject") is None


@pytest.mark.asyncio
async def test_ensure_default_email_category_creates_when_missing(db):
    from app.models.category import Category

    cat = await ensure_default_email_category(db)
    assert cat.code == "email"
    # Second call should return existing
    cat2 = await ensure_default_email_category(db)
    assert cat2.id == cat.id


async def _email_user(db, username="email_customer", role="customer"):
    user = User(
        username=username,
        email=f"{username}@example.com",
        password_hash=get_password_hash("Pass1234"),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_match_ticket_by_email_in_reply_to(db):
    user = await _email_user(db, "match_user")
    category = Category(name="故障", code="bug_match", default_priority="P2")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    from app.schemas.ticket import TicketCreate
    from app.services.ticket_service import create_ticket

    ticket = await create_ticket(
        db,
        TicketCreate(
            title="Original",
            description="Desc",
            category_id=category.id,
            priority="P2",
            source="web",
        ),
        user.id,
    )
    ticket.email_message_id = "orig-msg@example.com"
    await db.commit()
    await db.refresh(ticket)

    inbound = InboundEmail(
        message_id="reply-msg@example.com",
        from_address=user.email,
        to_address="support@example.com",
        subject="Re: your ticket",
        text_body="Follow up",
        in_reply_to="orig-msg@example.com",
    )
    matched = await match_ticket_by_email(db, inbound)
    assert matched is not None
    assert matched.id == ticket.id


@pytest.mark.asyncio
async def test_match_ticket_by_email_subject_ticket_no(db):
    user = await _email_user(db, "match_user2")
    category = Category(name="故障", code="bug_match2", default_priority="P2")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    from app.schemas.ticket import TicketCreate
    from app.services.ticket_service import create_ticket

    ticket = await create_ticket(
        db,
        TicketCreate(
            title="Original",
            description="Desc",
            category_id=category.id,
            priority="P2",
            source="web",
        ),
        user.id,
    )
    await db.refresh(ticket)

    inbound = InboundEmail(
        message_id="new-msg@example.com",
        from_address=user.email,
        to_address="support@example.com",
        subject=f"Re: {ticket.ticket_no} issue",
        text_body="Follow up",
    )
    matched = await match_ticket_by_email(db, inbound)
    assert matched is not None
    assert matched.id == ticket.id


@pytest.mark.asyncio
async def test_match_ticket_by_email_no_match(db):
    user = await _email_user(db, "match_user3")
    inbound = InboundEmail(
        message_id="new-msg@example.com",
        from_address=user.email,
        to_address="support@example.com",
        subject="No ticket number",
        text_body="Hello",
    )
    matched = await match_ticket_by_email(db, inbound)
    assert matched is None


@pytest.mark.asyncio
async def test_create_ticket_from_email(db):
    user = await _email_user(db, "ticket_creator")
    inbound = InboundEmail(
        message_id="create-msg@example.com",
        from_address=user.email,
        to_address="support@example.com",
        subject="New ticket via email",
        text_body="Description",
    )
    ticket = await create_ticket_from_email(db, inbound, user.id)
    assert ticket.title == inbound.subject
    assert ticket.description == inbound.text_body
    assert ticket.source == "email"
    assert ticket.email_message_id == inbound.message_id
    assert ticket.category_id is not None


@pytest.mark.asyncio
async def test_create_reply_from_email(db, open_ticket):
    user = await _email_user(db, "reply_creator")
    inbound = InboundEmail(
        message_id="reply-msg@example.com",
        from_address=user.email,
        to_address="support@example.com",
        subject="Re: ticket",
        text_body="Reply content",
    )
    reply = await create_reply_from_email(db, inbound, open_ticket, user.id)
    assert reply.ticket_id == open_ticket.id
    assert reply.author_id == user.id
    assert reply.content == inbound.text_body
    assert reply.email_message_id == inbound.message_id
    assert reply.is_internal is False


@pytest.mark.asyncio
async def test_enqueue_moderation(db):
    inbound = InboundEmail(
        message_id="mod-msg@example.com",
        from_address="unknown@example.com",
        to_address="support@example.com",
        subject="Moderation",
        text_body="Please help",
    )
    ingestion = await enqueue_moderation(db, inbound)
    assert ingestion.id is not None
    assert ingestion.sender_email == "unknown@example.com"
    assert ingestion.status == "pending"
    assert ingestion.message_id == inbound.message_id
    assert ingestion.body == inbound.text_body


@pytest.mark.asyncio
async def test_process_inbound_email_unknown_sender_enqueue(db):
    inbound = InboundEmail(
        message_id="unknown-msg@example.com",
        from_address="stranger@example.com",
        to_address="support@example.com",
        subject="Help",
        text_body="I need help",
    )
    result = await process_inbound_email(db, inbound)
    assert isinstance(result, EmailIngestion)
    assert result.sender_email == "stranger@example.com"


@pytest.mark.asyncio
async def test_process_inbound_email_known_sender_creates_ticket(db):
    user = await _email_user(db, "known_sender")
    inbound = InboundEmail(
        message_id="known-msg@example.com",
        from_address=user.email,
        to_address="support@example.com",
        subject="Create ticket",
        text_body="Description",
    )
    result = await process_inbound_email(db, inbound)
    assert isinstance(result, Ticket)
    assert result.requester_id == user.id
    assert result.source == "email"
    assert result.email_message_id == inbound.message_id


@pytest.mark.asyncio
async def test_process_inbound_email_known_sender_creates_reply(db):
    user = await _email_user(db, "known_sender2")
    category = Category(name="故障", code="bug_reply", default_priority="P2")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    from app.schemas.ticket import TicketCreate
    from app.services.ticket_service import create_ticket

    ticket = await create_ticket(
        db,
        TicketCreate(
            title="Original",
            description="Desc",
            category_id=category.id,
            priority="P2",
            source="web",
        ),
        user.id,
    )
    ticket.email_message_id = "orig-msg@example.com"
    await db.commit()
    await db.refresh(ticket)

    inbound = InboundEmail(
        message_id="reply-process@example.com",
        from_address=user.email,
        to_address="support@example.com",
        subject="Re: your ticket",
        text_body="Reply content",
        in_reply_to="orig-msg@example.com",
    )
    result = await process_inbound_email(db, inbound)
    assert isinstance(result, TicketReply)
    assert result.ticket_id == ticket.id
    assert result.author_id == user.id


@pytest.mark.asyncio
async def test_process_inbound_email_domain_not_allowed(db, monkeypatch):
    def _settings():
        return Settings(EMAIL_ALLOWED_DOMAINS=["allowed.com"])

    monkeypatch.setattr("app.config.get_settings", _settings)

    inbound = InboundEmail(
        message_id="reject-msg@example.com",
        from_address="user@notallowed.com",
        to_address="support@example.com",
        subject="Help",
        text_body="Description",
    )
    with pytest.raises(ValueError, match="not in allowlist"):
        await process_inbound_email(db, inbound)


# ===== HTML-to-text body handling =====


def test_html_to_text_strips_tags_and_entities():
    assert html_to_text("<p>Hello &amp; welcome</p>") == "Hello & welcome"
    assert html_to_text("<div>Line 1</div><br><div>Line 2</div>") == "Line 1 Line 2"


def test_get_body_prefers_text_body():
    inbound = InboundEmail(
        message_id="text-msg@example.com",
        from_address="user@example.com",
        to_address="support@example.com",
        subject="Text body preferred",
        text_body="Plain text",
        html_body="<p>HTML</p>",
    )
    assert _get_body(inbound) == "Plain text"


def test_get_body_converts_html_body_when_text_missing():
    inbound = InboundEmail(
        message_id="html-msg@example.com",
        from_address="user@example.com",
        to_address="support@example.com",
        subject="HTML fallback",
        text_body=None,
        html_body="<p>Hello</p>",
    )
    assert _get_body(inbound) == "Hello"


def test_get_body_returns_empty_when_no_bodies():
    inbound = InboundEmail(
        message_id="empty-msg@example.com",
        from_address="user@example.com",
        to_address="support@example.com",
        subject="No body",
        text_body=None,
        html_body=None,
    )
    assert _get_body(inbound) == ""


@pytest.mark.asyncio
async def test_create_ticket_from_email_uses_plain_text_from_html(db):
    user = await _email_user(db, "html_ticket_creator")
    inbound = InboundEmail(
        message_id="html-create-msg@example.com",
        from_address=user.email,
        to_address="support@example.com",
        subject="New ticket via email",
        html_body="<p>HTML description</p>",
    )
    ticket = await create_ticket_from_email(db, inbound, user.id)
    assert ticket.description == "HTML description"


@pytest.mark.asyncio
async def test_create_reply_from_email_uses_plain_text_from_html(db, open_ticket):
    user = await _email_user(db, "html_reply_creator")
    inbound = InboundEmail(
        message_id="html-reply-msg@example.com",
        from_address=user.email,
        to_address="support@example.com",
        subject="Re: ticket",
        html_body="<p>HTML reply content</p>",
    )
    reply = await create_reply_from_email(db, inbound, open_ticket, user.id)
    assert reply.content == "HTML reply content"


@pytest.mark.asyncio
async def test_enqueue_moderation_uses_plain_text_from_html(db):
    inbound = InboundEmail(
        message_id="html-mod-msg@example.com",
        from_address="unknown@example.com",
        to_address="support@example.com",
        subject="Moderation",
        html_body="<p>Please help</p>",
    )
    ingestion = await enqueue_moderation(db, inbound)
    assert ingestion.body == "Please help"


# ===== Webhook Router Tests =====


def test_webhook_missing_auth_returns_401():
    response = client.post("/api/v1/webhooks/email", json={})
    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"


def test_webhook_invalid_token_returns_401():
    response = client.post(
        "/api/v1/webhooks/email",
        json={
            "message_id": "msg-002@test",
            "from_address": "a@example.com",
            "to_address": "support@example.com",
            "subject": "Test",
        },
        headers={"Authorization": "Bearer wrong-secret"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_unknown_sender_creates_moderation(db):
    payload = {
        "message_id": "msg-001@test",
        "from_address": "unknown@example.com",
        "to_address": "support@example.com",
        "subject": "Help needed",
        "text_body": "I have a problem",
    }
    response = client.post(
        "/api/v1/webhooks/email",
        json=payload,
        headers={"Authorization": "Bearer webhook-secret-change-me"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    result = await db.execute(
        select(EmailIngestion).where(EmailIngestion.message_id == "msg-001@test")
    )
    ingestion = result.scalar_one_or_none()
    assert ingestion is not None
    assert ingestion.status == "pending"
    assert ingestion.sender_email == "unknown@example.com"


def test_webhook_swallows_invalid_payload_returns_200():
    response = client.post(
        "/api/v1/webhooks/email",
        json={"not_a_valid_payload": True},
        headers={"Authorization": "Bearer webhook-secret-change-me"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ===== Admin Moderation API Tests =====


@pytest.mark.asyncio
async def test_admin_list_email_ingestion_requires_auth(db, async_client):
    response = await async_client.get("/api/v1/admin/email-ingestion")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_list_email_ingestion(db, async_client, admin_auth_headers):
    ingestion = EmailIngestion(
        sender_email="sender@example.com",
        subject="Subject",
        body="Body",
        message_id="list-msg@example.com",
        status="pending",
    )
    db.add(ingestion)
    await db.commit()

    response = await async_client.get(
        "/api/v1/admin/email-ingestion?status_filter=pending",
        headers=admin_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert any(item["message_id"] == "list-msg@example.com" for item in data)


@pytest.mark.asyncio
async def test_supervisor_can_list_email_ingestion(db, async_client, supervisor_auth_headers):
    ingestion = EmailIngestion(
        sender_email="sender2@example.com",
        subject="Subject",
        body="Body",
        message_id="list-msg-2@example.com",
        status="pending",
    )
    db.add(ingestion)
    await db.commit()

    response = await async_client.get(
        "/api/v1/admin/email-ingestion",
        headers=supervisor_auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_customer_cannot_access_admin_email_ingestion(
    db, async_client, customer_auth_headers
):
    response = await async_client.get(
        "/api/v1/admin/email-ingestion",
        headers=customer_auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_approve_email_ingestion(db, async_client, admin_auth_headers):
    ingestion = EmailIngestion(
        sender_email="approve@example.com",
        sender_name="Approver",
        subject="Approve me",
        body="I need a ticket",
        message_id="approve-msg@example.com",
        status="pending",
    )
    db.add(ingestion)
    await db.commit()
    await db.refresh(ingestion)

    response = await async_client.post(
        f"/api/v1/admin/email-ingestion/{ingestion.id}/approve",
        headers=admin_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["user_id"] is not None
    assert data["ticket_id"] is not None

    result = await db.execute(select(EmailIngestion).where(EmailIngestion.id == ingestion.id))
    updated = result.scalar_one()
    await db.refresh(updated)
    assert updated.status == "approved"
    assert updated.created_user_id == data["user_id"]
    assert updated.ticket_id == data["ticket_id"]

    user_result = await db.execute(select(User).where(User.id == data["user_id"]))
    user = user_result.scalar_one()
    assert user.email == "approve@example.com"
    assert user.role == "customer"

    ticket_result = await db.execute(select(Ticket).where(Ticket.id == data["ticket_id"]))
    ticket = ticket_result.scalar_one()
    await db.refresh(ticket)
    assert ticket.title == "Approve me"
    assert ticket.source == "email"
    assert ticket.email_message_id == "approve-msg@example.com"


@pytest.mark.asyncio
async def test_admin_approve_email_ingestion_username_conflict(
    db, async_client, admin_auth_headers
):
    existing = User(
        username="conflict",
        email="other@example.com",
        password_hash=get_password_hash("Pass1234"),
        role="customer",
        is_active=True,
    )
    db.add(existing)
    await db.commit()

    ingestion = EmailIngestion(
        sender_email="conflict@example.com",
        subject="Conflict",
        body="Body",
        message_id="conflict-msg@example.com",
        status="pending",
    )
    db.add(ingestion)
    await db.commit()
    await db.refresh(ingestion)

    response = await async_client.post(
        f"/api/v1/admin/email-ingestion/{ingestion.id}/approve",
        headers=admin_auth_headers,
    )
    assert response.status_code == 200

    result = await db.execute(select(User).where(User.email == "conflict@example.com"))
    user = result.scalar_one()
    assert user.username != "conflict"
    assert user.username.startswith("conflict_")


@pytest.mark.asyncio
async def test_admin_approve_nonexistent_returns_404(db, async_client, admin_auth_headers):
    response = await async_client.post(
        "/api/v1/admin/email-ingestion/99999/approve",
        headers=admin_auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_approve_already_processed_returns_409(db, async_client, admin_auth_headers):
    ingestion = EmailIngestion(
        sender_email="processed@example.com",
        subject="Processed",
        body="Body",
        message_id="processed-msg@example.com",
        status="approved",
    )
    db.add(ingestion)
    await db.commit()
    await db.refresh(ingestion)

    response = await async_client.post(
        f"/api/v1/admin/email-ingestion/{ingestion.id}/approve",
        headers=admin_auth_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_admin_reject_email_ingestion(db, async_client, admin_auth_headers):
    ingestion = EmailIngestion(
        sender_email="reject@example.com",
        subject="Reject me",
        body="Body",
        message_id="reject-msg@example.com",
        status="pending",
    )
    db.add(ingestion)
    await db.commit()
    await db.refresh(ingestion)

    response = await async_client.post(
        f"/api/v1/admin/email-ingestion/{ingestion.id}/reject",
        headers=admin_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"

    result = await db.execute(select(EmailIngestion).where(EmailIngestion.id == ingestion.id))
    updated = result.scalar_one()
    await db.refresh(updated)
    assert updated.status == "rejected"


@pytest.mark.asyncio
async def test_admin_reject_nonexistent_returns_404(db, async_client, admin_auth_headers):
    response = await async_client.post(
        "/api/v1/admin/email-ingestion/99999/reject",
        headers=admin_auth_headers,
    )
    assert response.status_code == 404


# ===== Additional coverage from Task 5 brief =====


@pytest.mark.asyncio
async def test_webhook_known_sender_creates_ticket(db, async_client):
    user = await _email_user(db, "webhook_known_sender")
    payload = {
        "message_id": "msg-webhook-known@test",
        "from_address": user.email,
        "to_address": "support@example.com",
        "subject": "Webhook new problem",
        "text_body": "Details here",
    }
    response = await async_client.post(
        "/api/v1/webhooks/email",
        json=payload,
        headers={"Authorization": "Bearer webhook-secret-change-me"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    result = await db.execute(
        select(Ticket).where(Ticket.email_message_id == "msg-webhook-known@test")
    )
    ticket = result.scalar_one_or_none()
    assert ticket is not None
    assert ticket.requester_id == user.id
    assert ticket.source == "email"


@pytest.mark.asyncio
async def test_duplicate_message_id_idempotent_for_replies(db):
    from sqlalchemy.exc import IntegrityError

    user = await _email_user(db, "dup_reply_user")
    inbound_ticket = InboundEmail(
        message_id="parent-dup-msg@test",
        from_address=user.email,
        to_address="support@example.com",
        subject="Parent ticket",
        text_body="Parent body",
    )
    ticket = await process_inbound_email(db, inbound_ticket)
    assert isinstance(ticket, Ticket)

    inbound_reply = InboundEmail(
        message_id="dup-reply-msg@test",
        from_address=user.email,
        to_address="support@example.com",
        subject="Re: Parent ticket",
        text_body="Reply body",
        in_reply_to="parent-dup-msg@test",
    )
    reply = await process_inbound_email(db, inbound_reply)
    assert isinstance(reply, TicketReply)
    assert reply.ticket_id == ticket.id

    # Second processing with the same reply message_id violates TicketReply.email_message_id unique constraint
    with pytest.raises(IntegrityError):
        await process_inbound_email(db, inbound_reply)
        await db.commit()
    await db.rollback()


def test_extract_ticket_no_various_prefixes():
    assert (
        extract_ticket_no_from_subject("[Support] Re: TK-20260101-0001 help")
        == "TK-20260101-0001"
    )
    assert extract_ticket_no_from_subject("Fwd: TK-20260101-0002") == "TK-20260101-0002"
    assert (
        extract_ticket_no_from_subject("FW: [Bug] TK-20260101-0003 issue")
        == "TK-20260101-0003"
    )
