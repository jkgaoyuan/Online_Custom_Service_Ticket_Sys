import asyncio
from app.database import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        print([row[0] for row in r])

asyncio.run(check())
