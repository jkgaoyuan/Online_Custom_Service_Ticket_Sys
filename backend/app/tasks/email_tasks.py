import asyncio
import logging

from celery import shared_task
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import get_settings
from app.schemas.email_webhook import InboundEmail
from app.services.email_service import process_inbound_email

logger = logging.getLogger(__name__)


@shared_task(name="tasks.process_inbound_email_task")
def process_inbound_email_task(payload: dict) -> None:
    """Process inbound email synchronously inside Celery (sync wrapper around async service)."""
    asyncio.run(_async_process(payload))


async def _async_process(payload: dict) -> None:
    """Create a fresh engine/session so this task is safe to run in any thread/process."""
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        future=True,
    )
    SessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    inbound = InboundEmail(**payload)
    async with SessionLocal() as db:
        try:
            await process_inbound_email(db, inbound)
            await db.commit()
        except IntegrityError:
            logger.warning(
                "Duplicate inbound email ignored: message_id=%s", inbound.message_id
            )
            await db.rollback()
        except Exception:
            logger.exception("Failed to process inbound email: %s", inbound.message_id)
            await db.rollback()
            raise
        finally:
            await engine.dispose()
