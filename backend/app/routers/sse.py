"""SSE endpoint for real-time notifications."""
import asyncio

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from starlette.requests import ClientDisconnect

from app.core.sse import add_client, remove_client
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/sse/connect")
async def sse_connect(current_user: User = Depends(get_current_user)):
    """Establish an SSE connection for the current user."""
    client_id, queue = await add_client(current_user.id)

    async def event_generator():
        try:
            while True:
                payload = await queue.get()
                yield f"data: {payload}\n\n"
        except (asyncio.CancelledError, ClientDisconnect):
            # Client disconnected
            pass
        finally:
            remove_client(current_user.id, client_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
