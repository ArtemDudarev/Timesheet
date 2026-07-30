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
from src.models.absence_type import AbsenceType
from src.models.employee import Employee
from src.database import get_async_session
from src.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
JWT_SECRET = "change-me-in-production"
JWT_ALGORITHM = "HS256"

# ── Фиксированные UUID ────────────────────────────────────────────────────────
EMPLOYEE_ID    = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
TEAMLEAD_ID    = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000002")
MANAGER_ID     = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000003")
OUTSIDER_ID    = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000004")
VACATION_TYPE_ID = uuid.UUID("00000000-0000-0000-0005-000000000001")
SICK_TYPE_ID     = uuid.UUID("00000000-0000-0000-0005-000000000002")


def create_test_token(sub: str, roles: list[str], permissions: list[str] | None = None) -> str:
    return jwt.encode(
        {
            "sub": sub,
            "roles": roles,
            "permissions": permissions if permissions is not None else [],
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

    mock_producer = AsyncMock()

    with (
        patch("src.main.KafkaEventProducer", return_value=mock_producer),
        patch("src.main.KafkaEventConsumer", return_value=AsyncMock()),
        patch("src.main.seed_absence_types", new_callable=AsyncMock),
        patch("src.main.engine") as mock_engine,
    ):
        mock_conn = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_engine.dispose = AsyncMock()
        app.state.kafka_producer = mock_producer

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


# ── Фикстуры данных ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def absence_types(db_session):
    types = [
        AbsenceType(id=VACATION_TYPE_ID, code="VACATION", name="Отпуск", color="#3B82F6", requires_approval=True),
        AbsenceType(id=SICK_TYPE_ID, code="SICK", name="Больничный", color="#F59E0B", requires_approval=True),
    ]
    db_session.add_all(types)
    await db_session.flush()
    return types


@pytest_asyncio.fixture
async def test_teamlead(db_session):
    lead = Employee(id=TEAMLEAD_ID, first_name="Пётр", last_name="Лидов")
    db_session.add(lead)
    await db_session.flush()
    return lead


@pytest_asyncio.fixture
async def test_employee(db_session, test_teamlead):
    employee = Employee(
        id=EMPLOYEE_ID, first_name="Иван", last_name="Петров", lead_id=TEAMLEAD_ID
    )
    db_session.add(employee)
    await db_session.flush()
    return employee


@pytest_asyncio.fixture
async def test_outsider(db_session):
    employee = Employee(id=OUTSIDER_ID, first_name="Олег", last_name="Чужой")
    db_session.add(employee)
    await db_session.flush()
    return employee


# ── Токены ────────────────────────────────────────────────────────────────────

@pytest.fixture
def employee_token():
    return create_test_token(str(EMPLOYEE_ID), ["Сотрудник"], [])


@pytest.fixture
def outsider_token():
    return create_test_token(str(OUTSIDER_ID), ["Сотрудник"], [])


@pytest.fixture
def teamlead_token():
    return create_test_token(
        str(TEAMLEAD_ID), ["Тимлид", "Сотрудник"],
        ["absence:read_team", "absence:approve_team"],
    )


@pytest.fixture
def manager_token():
    return create_test_token(
        str(MANAGER_ID), ["Менеджер", "Сотрудник"],
        ["absence:read_any", "absence:approve"],
    )
