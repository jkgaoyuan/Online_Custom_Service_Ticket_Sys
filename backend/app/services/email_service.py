import html
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.email_ingestion import EmailIngestion
from app.models.ticket import Ticket
from app.models.ticket_reply import TicketReply
from app.models.user import User
from app.schemas.email_webhook import InboundEmail
from app.schemas.ticket import TicketCreate
from app.services.ticket_service import create_ticket


_TICKET_NO_PATTERN = re.compile(r"(TK-\d{8}-\d{4})")


def html_to_text(html_body: str | None) -> str:
    """Convert raw HTML to a safe plain-text representation."""
    if not html_body:
        return ""
    text = re.sub(r"<[^>]+>", " ", html_body)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _get_body(inbound: InboundEmail) -> str:
    """Return the best available plain-text body for the inbound email."""
    return inbound.text_body or html_to_text(inbound.html_body) or ""


def extract_ticket_no_from_subject(subject: str) -> str | None:
    # Normalize: strip common prefixes and collapse whitespace
    normalized = subject
    for prefix in ("Re:", "Fwd:", "FW:"):
        if normalized.lower().startswith(prefix.lower()):
            normalized = normalized[len(prefix) :].strip()
    # Remove bracketed prefixes like [Support]
    normalized = re.sub(r"\[[^\]]+\]", "", normalized)
    normalized = " ".join(normalized.split())
    match = _TICKET_NO_PATTERN.search(normalized)
    return match.group(1) if match else None


async def ensure_default_email_category(db: AsyncSession) -> Category:
    result = await db.execute(select(Category).where(Category.code == "email"))
    cat = result.scalar_one_or_none()
    if cat:
        return cat
    cat = Category(
        name="邮件工单",
        code="email",
        description="通过邮件渠道创建的工单",
        default_priority="P2",
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


async def match_ticket_by_email(
    db: AsyncSession, inbound: InboundEmail
) -> Ticket | None:
    # Track 1: In-Reply-To -> Ticket.email_message_id
    if inbound.in_reply_to:
        result = await db.execute(
            select(Ticket).where(Ticket.email_message_id == inbound.in_reply_to)
        )
        ticket = result.scalar_one_or_none()
        if ticket:
            return ticket

    # Track 2: subject line regex -> ticket_no
    ticket_no = extract_ticket_no_from_subject(inbound.subject)
    if ticket_no:
        result = await db.execute(
            select(Ticket).where(Ticket.ticket_no == ticket_no)
        )
        ticket = result.scalar_one_or_none()
        if ticket:
            return ticket

    return None


async def create_ticket_from_email(
    db: AsyncSession, inbound: InboundEmail, user_id: int
) -> Ticket:
    category = await ensure_default_email_category(db)
    body = _get_body(inbound)
    data = TicketCreate(
        title=inbound.subject[:200],
        description=body,
        category_id=category.id,
        priority="P2",
        source="email",
    )
    ticket = await create_ticket(db, data, user_id)
    ticket.email_message_id = inbound.message_id
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def create_reply_from_email(
    db: AsyncSession, inbound: InboundEmail, ticket: Ticket, user_id: int
) -> TicketReply:
    body = _get_body(inbound)
    reply = TicketReply(
        ticket_id=ticket.id,
        author_id=user_id,
        content=body,
        is_internal=False,
        email_message_id=inbound.message_id,
    )
    db.add(reply)
    await db.commit()
    await db.refresh(reply)
    return reply


async def enqueue_moderation(
    db: AsyncSession, inbound: InboundEmail
) -> EmailIngestion:
    body = _get_body(inbound)
    ingestion = EmailIngestion(
        sender_email=str(inbound.from_address),
        sender_name=inbound.from_name,
        subject=inbound.subject,
        body=body,
        message_id=inbound.message_id,
        in_reply_to=inbound.in_reply_to,
    )
    db.add(ingestion)
    await db.commit()
    await db.refresh(ingestion)
    return ingestion


async def process_inbound_email(
    db: AsyncSession, inbound: InboundEmail
) -> Ticket | TicketReply | EmailIngestion:
    from app.config import get_settings

    settings = get_settings()

    # Domain allowlist check
    if settings.EMAIL_ALLOWED_DOMAINS:
        domain = str(inbound.from_address).split("@")[-1].lower()
        if domain not in [d.lower() for d in settings.EMAIL_ALLOWED_DOMAINS]:
            raise ValueError(f"Domain {domain} not in allowlist")

    # Lookup user by email
    result = await db.execute(
        select(User).where(User.email == str(inbound.from_address))
    )
    user = result.scalar_one_or_none()

    if not user:
        # Unknown sender -> moderation queue
        return await enqueue_moderation(db, inbound)

    # Match ticket
    ticket = await match_ticket_by_email(db, inbound)
    if ticket:
        return await create_reply_from_email(db, inbound, ticket, user.id)
    else:
        return await create_ticket_from_email(db, inbound, user.id)
