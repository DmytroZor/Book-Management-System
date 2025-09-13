
import pytest_asyncio
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db import get_db
from app.main import app
from app import models


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(TEST_DATABASE_URL, future=True, echo=False)
AsyncSessionTest = async_sessionmaker(
    bind=engine_test, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with AsyncSessionTest() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db



@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    async with engine_test.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(models.Base.metadata.drop_all)



@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionTest() as session:
        yield session





@pytest_asyncio.fixture
async def client_fixture():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

