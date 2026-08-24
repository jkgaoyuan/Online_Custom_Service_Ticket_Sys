import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://ticket_user:ticket_pass@localhost:5432/ticket_db"

async def fix():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        # 确认工单和客服信息
        result = await conn.execute(text(
            "SELECT id, ticket_no, status, assignee_id FROM tickets WHERE ticket_no = 'TK-20260824-0011'"
        ))
        ticket = result.fetchone()
        print(f"Ticket: {ticket}")

        result = await conn.execute(text(
            "SELECT id, username FROM users WHERE username = 'server2'"
        ))
        user = result.fetchone()
        print(f"User server2: {user}")

        if ticket and user:
            await conn.execute(text(
                "UPDATE tickets SET assignee_id = :agent_id WHERE id = :ticket_id"
            ), {"agent_id": user.id, "ticket_id": ticket.id})
            print(f"Fixed: set assignee_id = {user.id} for ticket {ticket.ticket_no}")
        else:
            print("Ticket or user not found, skipping")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix())
