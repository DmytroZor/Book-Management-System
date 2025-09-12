from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from config import settings

engine = create_async_engine(settings.database_url)
AsyncSessionLocal = async_sessionmaker(bind = engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
