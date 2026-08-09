import logging
import secrets

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies import require_role
from app.exceptions import DuplicateException, NotFoundException
from app.models.category import Category
from app.models.email_ingestion import EmailIngestion
from app.models.user import User
from app.schemas.email_webhook import InboundEmail
from app.schemas.ticket import TicketCreate
from app.services.auth_service import get_password_hash
from app.services.email_service import ensure_default_email_category
from app.services.ticket_service import create_ticket
from app.tasks.email_tasks import process_inbound_email_task

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_bearer_token(authorization: str | None) -> bool:
    settings = get_settings()
    expected = f"Bearer {settings.WEBHOOK_SECRET}"
    return authorization == expected


@router.post("/webhooks/email", status_code=status.HTTP_200_OK)
async def receive_email_webhook(
    request: Request,
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    if not verify_bearer_token(authorization):
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    try:
        payload = await request.json()
        inbound = InboundEmail(**payload)
        process_inbound_email_task.delay(inbound.model_dump())
    except Exception as exc:
        logger.exception("Webhook receive error: %s", exc)
        # Always return 200 to prevent provider retry storms
    return {"status": "ok"}


@router.get("/admin/email-ingestion", response_model=list[dict])
async def list_email_ingestion(
    status_filter: str = "pending",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
) -> list[dict]:
    result = await db.execute(select(EmailIngestion).where(EmailIngestion.status == status_filter))
    items = result.scalars().all()
    return [
        {
            "id": item.id,
            "sender_email": item.sender_email,
            "sender_name": item.sender_name,
            "subject": item.subject,
            "body": item.body,
            "message_id": item.message_id,
            "status": item.status,
            "received_at": item.received_at,
        }
        for item in items
    ]


@router.post("/admin/email-ingestion/{ingestion_id}/approve")
async def approve_email_ingestion(
    ingestion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
) -> dict:
    result = await db.execute(select(EmailIngestion).where(EmailIngestion.id == ingestion_id))
    ingestion = result.scalar_one_or_none()
    if not ingestion:
        raise NotFoundException("Ingestion not found")
    if ingestion.status != "pending":
        raise DuplicateException("Ingestion already processed")

    existing_user_result = await db.execute(
        select(User).where(User.email == ingestion.sender_email)
    )
    user = existing_user_result.scalar_one_or_none()

    if user is None:
        local_part = ingestion.sender_email.split("@")[0]
        username = local_part
        while True:
            result = await db.execute(select(User).where(User.username == username))
            if not result.scalar_one_or_none():
                break
            username = f"{local_part}_{secrets.token_hex(2)}"

        user = User(
            username=username,
            email=ingestion.sender_email,
            password_hash=get_password_hash(secrets.token_urlsafe(24)),
            role="customer",
            is_active=True,
        )
        db.add(user)
        await db.flush()

    category = await ensure_default_email_category(db)
    data = TicketCreate(
        title=ingestion.subject[:200],
        description=ingestion.body,
        category_id=category.id,
        priority="P2",
        source="email",
    )
    ticket = await create_ticket(db, data, user.id)
    ticket.email_message_id = ingestion.message_id
    await db.flush()

    ingestion.status = "approved"
    ingestion.created_user_id = user.id
    ingestion.ticket_id = ticket.id
    await db.commit()

    return {"status": "approved", "user_id": user.id, "ticket_id": ticket.id}


@router.post("/admin/email-ingestion/{ingestion_id}/reject")
async def reject_email_ingestion(
    ingestion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
) -> dict:
    result = await db.execute(select(EmailIngestion).where(EmailIngestion.id == ingestion_id))
    ingestion = result.scalar_one_or_none()
    if not ingestion:
        raise NotFoundException("Ingestion not found")
    if ingestion.status != "pending":
        raise DuplicateException("Ingestion already processed")
    ingestion.status = "rejected"
    await db.commit()
    return {"status": "rejected"}
