import asyncio
from app.database import engine
from sqlalchemy import text

async def reset():
    async with engine.connect() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
        await conn.commit()
    print("Dropped alembic_version")

asyncio.run(reset())
