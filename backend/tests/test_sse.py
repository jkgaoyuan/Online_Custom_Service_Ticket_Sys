import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.sse import add_client, remove_client, send_event
from app.main import app


@pytest.fixture(autouse=True)
async def setup_db():
    """Override global setup_db: SSE tests don't need the database."""
    yield


async def test_sse_connect_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/sse/connect")
    assert r.status_code == 401


async def test_sse_add_and_remove_client():
    user_id = 999
    client_id, queue = await add_client(user_id)
    assert client_id is not None
    assert isinstance(queue, asyncio.Queue)
    assert user_id in send_event.__globals__["sse_clients"]

    remove_client(user_id, client_id)
    assert user_id not in send_event.__globals__["sse_clients"]


async def test_sse_send_event_received_by_client():
    user_id = 998
    client_id, queue = await add_client(user_id)
    try:
        await send_event(user_id, "new_notification", {"message": "hello"})
        payload = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert '"type": "new_notification"' in payload
        assert '"message": "hello"' in payload
    finally:
        remove_client(user_id, client_id)


async def test_sse_send_event_to_multiple_clients():
    user_id = 997
    client_id1, queue1 = await add_client(user_id)
    client_id2, queue2 = await add_client(user_id)
    try:
        await send_event(user_id, "new_notification", {"id": 1})
        payload1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
        payload2 = await asyncio.wait_for(queue2.get(), timeout=1.0)
        assert payload1 == payload2
        assert '"id": 1' in payload1
    finally:
        remove_client(user_id, client_id1)
        remove_client(user_id, client_id2)


async def test_sse_send_event_to_nonexistent_user():
    # Should not raise when user has no connected clients
    await send_event(999999, "new_notification", {"msg": "test"})
