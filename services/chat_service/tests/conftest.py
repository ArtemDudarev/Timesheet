import time
import uuid
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from jose import jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.models.base import Base
from src.models.channel import Channel, ChannelMember, ChannelType
from src.models.employee import Employee
from src.models.project import Project
from src.database import get_async_session
from src.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
JWT_SECRET = "change-me-in-production"
JWT_ALGORITHM = "HS256"

# ── Фиксированные UUID ────────────────────────────────────────────────────────
ALICE_ID   = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
BOB_ID     = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000002")
CAROL_ID   = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000003")
PROJECT_ID = uuid.UUID("33333333-0000-0000-0000-000000000001")
CHANNEL_ID = uuid.UUID("44444444-0000-0000-0000-000000000001")


def create_test_token(sub: str) -> str:
    return jwt.encode(
        {
            "sub": sub,
            "roles": ["Сотрудник"],
            "permissions": [],
            "is_active": True,
            "exp": int(time.time()) + 3600,
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


# ── Инфраструктурные фикстуры ─────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    Session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with Session() as session:
        await session.execute(text("PRAGMA foreign_keys=ON"))
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_get_session

    with (
        patch("src.main.KafkaEventConsumer", return_value=AsyncMock()),
        patch("src.main.engine") as mock_engine,
    ):
        mock_conn = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_engine.dispose = AsyncMock()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


# ── Фикстуры данных ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_employees(db_session):
    employees = [
        Employee(id=ALICE_ID, first_name="Алиса", last_name="Иванова"),
        Employee(id=BOB_ID, first_name="Борис", last_name="Петров"),
        Employee(id=CAROL_ID, first_name="Карина", last_name="Чужая"),
    ]
    db_session.add_all(employees)
    await db_session.flush()
    return employees


@pytest_asyncio.fixture
async def project_channel(db_session, test_employees):
    """Групповой канал проекта: Алиса и Борис — участники, Карина — нет."""
    db_session.add(Project(id=PROJECT_ID, name="Внутренний портал"))
    channel = Channel(
        id=CHANNEL_ID,
        type=ChannelType.GROUP,
        name="Внутренний портал",
        project_id=PROJECT_ID,
        members=[
            ChannelMember(employee_id=ALICE_ID),
            ChannelMember(employee_id=BOB_ID),
        ],
    )
    db_session.add(channel)
    await db_session.flush()
    return channel


# ── Токены ────────────────────────────────────────────────────────────────────

@pytest.fixture
def alice_token():
    return create_test_token(str(ALICE_ID))


@pytest.fixture
def bob_token():
    return create_test_token(str(BOB_ID))


@pytest.fixture
def carol_token():
    return create_test_token(str(CAROL_ID))
