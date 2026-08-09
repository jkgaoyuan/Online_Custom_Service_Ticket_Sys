import logging
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger(__name__)


class Mailer:
    async def send_text_email(self, to: str, subject: str, body: str) -> None:
        settings = get_settings()
        if settings.SMTP_HOST:
            await self._send_via_smtp(to, subject, body)
        elif settings.EMAIL_API_PROVIDER:
            logger.warning("HTTP API mailer not implemented in MVP")
        else:
            logger.warning("No mailer configured; email skipped")

    async def _send_via_smtp(self, to: str, subject: str, body: str) -> None:
        # Import aiosmtplib only when needed to avoid hard dependency in tests
        try:
            import aiosmtplib
        except ImportError:
            logger.error("aiosmtplib not installed; cannot send SMTP email")
            return

        settings = get_settings()
        sender = settings.EMAIL_FROM or settings.SMTP_USER
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = to
        message.set_content(body)
        await aiosmtplib.send(
            message=message,
            sender=sender,
            recipients=[to],
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=settings.SMTP_TLS,
        )
