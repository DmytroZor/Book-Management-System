from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.ext.asyncio import AsyncConnection
from app.config import settings

engine: AsyncEngine = create_async_engine(settings.database_url, future=True, echo=False)


async def get_conn():
    async with engine.connect() as conn:
        yield conn

