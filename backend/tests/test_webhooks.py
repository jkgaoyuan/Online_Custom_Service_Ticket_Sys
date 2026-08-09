from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.email_ingestion import EmailIngestion
from app.models.ticket_reply import TicketReply
from app.models.user import User
from app.utils.security import get_password_hash


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


async def test_ticket_reply_email_message_id(db, open_ticket, agent_auth_headers):
    result = await db.execute(
        select(User).where(User.username == "agent_test")
    )
    agent = result.scalar_one()

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


async def test_ticket_reply_email_message_id_unique(db, open_ticket, agent_auth_headers):
    result = await db.execute(
        select(User).where(User.username == "agent_test")
    )
    agent = result.scalar_one()

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
