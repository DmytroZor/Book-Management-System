import pytest_asyncio
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from app.main import app
from app import models
from app.db import get_conn

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test: AsyncEngine = create_async_engine(TEST_DATABASE_URL, future=True, echo=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    async with engine_test.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(models.Base.metadata.drop_all)


async def override_get_conn():
    async with engine_test.connect() as conn:
        yield conn


app.dependency_overrides[get_conn] = override_get_conn


@pytest_asyncio.fixture
async def client_fixture():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def db_conn():
    async with engine_test.connect() as conn:
        yield conn
