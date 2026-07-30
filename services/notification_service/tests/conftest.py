import time
import uuid
import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from jose import jwt
from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.models.base import Base
from src.models.employee import Employee
from src.models.notification import Notification, NotificationType
from src.models.role import Role
from src.models.user import User
from src.models.user_role import user_role
from src.database import get_async_session
from src.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
JWT_SECRET = "change-me-in-production"
JWT_ALGORITHM = "HS256"

# ── Фиксированные UUID ────────────────────────────────────────────────────────
EMPLOYEE_ROLE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
MANAGER_ROLE_ID  = uuid.UUID("00000000-0000-0000-0000-000000000002")
EMPLOYEE_ID      = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
TEAMLEAD_ID      = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000002")
MANAGER_ID       = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000003")
NOTIFICATION_ID  = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000001")


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
async def manager_user(db_session):
    role = Role(id=MANAGER_ROLE_ID, name="Менеджер", description="Управляющая роль")
    user = User(id=MANAGER_ID, email="manager@test.com", is_active=True)
    db_session.add_all([role, user])
    await db_session.flush()
    await db_session.execute(
        insert(user_role).values(user_id=MANAGER_ID, role_id=MANAGER_ROLE_ID)
    )
    await db_session.flush()
    return user


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
async def test_employee_without_lead(db_session):
    employee = Employee(id=EMPLOYEE_ID, first_name="Иван", last_name="Петров")
    db_session.add(employee)
    await db_session.flush()
    return employee


@pytest_asyncio.fixture
async def test_notification(db_session):
    notification = Notification(
        id=NOTIFICATION_ID,
        user_id=EMPLOYEE_ID,
        type=NotificationType.APPROVAL,
        title="Табель согласован",
        text="Ваш табель за 06.2026 согласован",
        created_at=datetime(2026, 7, 1, 12, 0, 0),
    )
    db_session.add(notification)
    await db_session.flush()
    return notification


# ── Токены ────────────────────────────────────────────────────────────────────

@pytest.fixture
def employee_token():
    return create_test_token(str(EMPLOYEE_ID))


@pytest.fixture
def teamlead_token():
    return create_test_token(str(TEAMLEAD_ID))
