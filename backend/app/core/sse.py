"""Server-Sent Events connection manager."""
import asyncio
import json
import uuid
from collections import defaultdict

# user_id -> list of (client_id, queue)
sse_clients: dict[int, list[tuple[str, asyncio.Queue]]] = defaultdict(list)


async def add_client(user_id: int) -> tuple[str, asyncio.Queue]:
    """Add a new SSE client for a user. Returns (client_id, queue)."""
    client_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    sse_clients[user_id].append((client_id, queue))
    return client_id, queue


def remove_client(user_id: int, client_id: str) -> None:
    """Remove an SSE client."""
    clients = sse_clients.get(user_id, [])
    sse_clients[user_id] = [(cid, q) for cid, q in clients if cid != client_id]
    if not sse_clients[user_id]:
        del sse_clients[user_id]


async def send_event(user_id: int, event_type: str, data: dict) -> None:
    """Send an event to all connected clients of a user."""
    clients = sse_clients.get(user_id, [])
    if not clients:
        return
    payload = json.dumps({"type": event_type, "data": data})
    for _, queue in clients:
        await queue.put(payload)
