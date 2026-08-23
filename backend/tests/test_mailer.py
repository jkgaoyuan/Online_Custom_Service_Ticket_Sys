import builtins
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.mailer import Mailer

pytestmark = pytest.mark.anyio


class TestMailerSendTextEmail:
    async def test_smtp_success(self):
        mock_settings = MagicMock()
        mock_settings.SMTP_HOST = "smtp.example.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USER = "user@example.com"
        mock_settings.SMTP_PASSWORD = "secret"
        mock_settings.SMTP_TLS = True
        mock_settings.EMAIL_FROM = "from@example.com"
        mock_settings.EMAIL_API_PROVIDER = None

        mock_aiosmtplib = MagicMock()
        mock_aiosmtplib.send = AsyncMock()

        with patch("app.services.mailer.get_settings", return_value=mock_settings):
            with patch.dict("sys.modules", {"aiosmtplib": mock_aiosmtplib}):
                mailer = Mailer()
                await mailer.send_text_email("to@example.com", "Subject", "Body")

        mock_aiosmtplib.send.assert_awaited_once()
        call_kwargs = mock_aiosmtplib.send.call_args.kwargs
        msg = call_kwargs["message"]
        assert msg["Subject"] == "Subject"
        assert msg["From"] == "from@example.com"
        assert msg["To"] == "to@example.com"
        assert "Body" in msg.get_content()
        assert call_kwargs["hostname"] == "smtp.example.com"
        assert call_kwargs["port"] == 587
        assert call_kwargs["username"] == "user@example.com"
        assert call_kwargs["password"] == "secret"
        assert call_kwargs["start_tls"] is True

    async def test_smtp_fallback_sender(self):
        mock_settings = MagicMock()
        mock_settings.SMTP_HOST = "smtp.example.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USER = "user@example.com"
        mock_settings.SMTP_PASSWORD = "secret"
        mock_settings.SMTP_TLS = True
        mock_settings.EMAIL_FROM = None
        mock_settings.EMAIL_API_PROVIDER = None

        mock_aiosmtplib = MagicMock()
        mock_aiosmtplib.send = AsyncMock()

        with patch("app.services.mailer.get_settings", return_value=mock_settings):
            with patch.dict("sys.modules", {"aiosmtplib": mock_aiosmtplib}):
                mailer = Mailer()
                await mailer.send_text_email("to@example.com", "Subject", "Body")

        msg = mock_aiosmtplib.send.call_args.kwargs["message"]
        assert msg["From"] == "user@example.com"

    async def test_aiosmtplib_not_installed(self, caplog):
        mock_settings = MagicMock()
        mock_settings.SMTP_HOST = "smtp.example.com"
        mock_settings.EMAIL_API_PROVIDER = None

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "aiosmtplib":
                raise ImportError("No module named 'aiosmtplib'")
            return real_import(name, *args, **kwargs)

        with patch("app.services.mailer.get_settings", return_value=mock_settings):
            with patch.object(builtins, "__import__", fake_import):
                mailer = Mailer()
                with caplog.at_level(logging.ERROR, logger="app.services.mailer"):
                    await mailer.send_text_email("to@example.com", "Subject", "Body")

        assert "aiosmtplib not installed" in caplog.text

    async def test_api_provider_warning(self, caplog):
        mock_settings = MagicMock()
        mock_settings.SMTP_HOST = None
        mock_settings.EMAIL_API_PROVIDER = "sendgrid"

        with patch("app.services.mailer.get_settings", return_value=mock_settings):
            mailer = Mailer()
            with caplog.at_level(logging.WARNING, logger="app.services.mailer"):
                await mailer.send_text_email("to@example.com", "Subject", "Body")

        assert "HTTP API mailer not implemented" in caplog.text

    async def test_no_config_warning(self, caplog):
        mock_settings = MagicMock()
        mock_settings.SMTP_HOST = None
        mock_settings.EMAIL_API_PROVIDER = None

        with patch("app.services.mailer.get_settings", return_value=mock_settings):
            mailer = Mailer()
            with caplog.at_level(logging.WARNING, logger="app.services.mailer"):
                await mailer.send_text_email("to@example.com", "Subject", "Body")

        assert "No mailer configured" in caplog.text
