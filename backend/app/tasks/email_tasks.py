import asyncio
import logging

from celery import shared_task

from app.database import AsyncSessionLocal
from app.schemas.email_webhook import InboundEmail
from app.services.email_service import process_inbound_email

logger = logging.getLogger(__name__)


@shared_task(name="tasks.process_inbound_email_task")
def process_inbound_email_task(payload: dict) -> None:
    """Process inbound email synchronously inside Celery (sync wrapper around async service)."""
    asyncio.run(_async_process(payload))


async def _async_process(payload: dict) -> None:
    inbound = InboundEmail(**payload)
    async with AsyncSessionLocal() as db:
        try:
            await process_inbound_email(db, inbound)
            await db.commit()
        except Exception:
            logger.exception("Failed to process inbound email: %s", inbound.message_id)
            await db.rollback()
            raise
