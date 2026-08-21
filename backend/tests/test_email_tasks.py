import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.tasks.email_tasks import process_inbound_email_task, _async_process
from app.schemas.email_webhook import InboundEmail


class TestProcessInboundEmailTask:
    def test_sync_wrapper_calls_async(self):
        payload = {
            "from_address": "test@example.com",
            "to_address": "support@example.com",
            "from_name": "Test",
            "subject": "Hello",
            "text_body": "World",
            "html_body": None,
            "message_id": "msg-001",
            "in_reply_to": None,
        }
        with patch("app.tasks.email_tasks._async_process") as mock_async:
            mock_async.return_value = None
            process_inbound_email_task(payload)
            mock_async.assert_called_once_with(payload)


class TestAsyncProcess:
    @pytest.mark.anyio
    async def test_successful_processing(self):
        payload = {
            "from_address": "test@example.com",
            "to_address": "support@example.com",
            "from_name": "Test",
            "subject": "Hello",
            "text_body": "World",
            "html_body": None,
            "message_id": "msg-002",
            "in_reply_to": None,
        }

        mock_db = AsyncMock()
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.email_tasks.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                DATABASE_URL="postgresql+asyncpg://test",
                DEBUG=False,
            )
            with patch("app.tasks.email_tasks.create_async_engine", return_value=mock_engine):
                with patch("app.tasks.email_tasks.async_sessionmaker", return_value=MagicMock(return_value=mock_db)):
                    with patch("app.tasks.email_tasks.process_inbound_email", new_callable=AsyncMock) as mock_process:
                        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
                        mock_db.__aexit__ = AsyncMock(return_value=False)
                        await _async_process(payload)
                        mock_process.assert_called_once()
                        inbound = mock_process.call_args[0][1]
                        assert isinstance(inbound, InboundEmail)
                        assert inbound.message_id == "msg-002"

    @pytest.mark.anyio
    async def test_integrity_error_rollback(self):
        payload = {
            "from_address": "test@example.com",
            "to_address": "support@example.com",
            "from_name": "Test",
            "subject": "Hello",
            "text_body": "World",
            "html_body": None,
            "message_id": "msg-003",
            "in_reply_to": None,
        }

        from sqlalchemy.exc import IntegrityError

        mock_db = AsyncMock()
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.email_tasks.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                DATABASE_URL="postgresql+asyncpg://test",
                DEBUG=False,
            )
            with patch("app.tasks.email_tasks.create_async_engine", return_value=mock_engine):
                with patch("app.tasks.email_tasks.async_sessionmaker", return_value=MagicMock(return_value=mock_db)):
                    with patch("app.tasks.email_tasks.process_inbound_email", new_callable=AsyncMock) as mock_process:
                        mock_process.side_effect = IntegrityError("stmt", {}, Exception("dup"))
                        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
                        mock_db.__aexit__ = AsyncMock(return_value=False)
                        # Should not raise
                        await _async_process(payload)
                        mock_db.rollback.assert_called_once()

    @pytest.mark.anyio
    async def test_generic_exception_rollback_and_reraise(self):
        payload = {
            "from_address": "test@example.com",
            "to_address": "support@example.com",
            "from_name": "Test",
            "subject": "Hello",
            "text_body": "World",
            "html_body": None,
            "message_id": "msg-004",
            "in_reply_to": None,
        }

        mock_db = AsyncMock()
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.email_tasks.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                DATABASE_URL="postgresql+asyncpg://test",
                DEBUG=False,
            )
            with patch("app.tasks.email_tasks.create_async_engine", return_value=mock_engine):
                with patch("app.tasks.email_tasks.async_sessionmaker", return_value=MagicMock(return_value=mock_db)):
                    with patch("app.tasks.email_tasks.process_inbound_email", new_callable=AsyncMock) as mock_process:
                        mock_process.side_effect = ValueError("bad email")
                        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
                        mock_db.__aexit__ = AsyncMock(return_value=False)
                        with pytest.raises(ValueError, match="bad email"):
                            await _async_process(payload)
                        mock_db.rollback.assert_called_once()
