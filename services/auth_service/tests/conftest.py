import uuid
import pytest
import pytest_asyncio
from datetime import date
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.models.base import Base
from src.models.role import Role
from src.models.user import User
from src.models.user_role import user_role
from src.database import get_async_session
from src.security import create_access_token
from src.services.employee_service import UserService
from src.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

# ── Фиксированные UUID ────────────────────────────────────────────────────────
EMPLOYEE_ROLE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
MANAGER_ROLE_ID  = uuid.UUID("00000000-0000-0000-0000-000000000002")
REGULAR_USER_ID  = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
MANAGER_USER_ID  = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000002")


# ── Инфраструктурные фикстуры ─────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_engine():
    """Свежая SQLite-база для каждого теста."""
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Сессия к тестовой БД. После теста — rollback."""
    Session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """HTTP-клиент с замоканной Kafka и тестовой БД."""
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_get_session

    mock_producer = AsyncMock()

    with (
        patch("src.main.KafkaEventProducer", return_value=mock_producer),
        patch("src.main.KafkaEventConsumer", return_value=AsyncMock()),
        patch("src.main.seed_roles", new_callable=AsyncMock),
        patch("src.main.seed_demo_users", new_callable=AsyncMock),
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


# ── Фикстуры ролей ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def employee_role(db_session):
    role = Role(id=EMPLOYEE_ROLE_ID, name="Сотрудник", description="Базовая роль")
    db_session.add(role)
    await db_session.flush()
    return role


@pytest_asyncio.fixture
async def manager_role(db_session):
    role = Role(id=MANAGER_ROLE_ID, name="Менеджер", description="Роль с правами управления")
    db_session.add(role)
    await db_session.flush()
    return role


# ── Фикстуры пользователей ────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def regular_user(db_session, employee_role):
    """Обычный сотрудник в тестовой БД."""
    service = UserService(db_session)
    user = User(
        id=REGULAR_USER_ID,
        email="employee@test.com",
        number="EMP-100001",
        hashed_password=service.hash_password("Employee1!"),
        is_active=True,
        must_change_password=False,
        register_date=date.today(),
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.execute(
        insert(user_role).values(user_id=REGULAR_USER_ID, role_id=EMPLOYEE_ROLE_ID)
    )
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def manager_user(db_session, employee_role, manager_role):
    """Менеджер в тестовой БД."""
    service = UserService(db_session)
    user = User(
        id=MANAGER_USER_ID,
        email="manager@test.com",
        number="EMP-100002",
        hashed_password=service.hash_password("Manager1!"),
        is_active=True,
        must_change_password=False,
        register_date=date.today(),
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.execute(
        insert(user_role).values([
            {"user_id": MANAGER_USER_ID, "role_id": MANAGER_ROLE_ID},
            {"user_id": MANAGER_USER_ID, "role_id": EMPLOYEE_ROLE_ID},
        ])
    )
    await db_session.flush()
    return user


# ── Фикстура refresh-токена ───────────────────────────────────────────────────

@pytest_asyncio.fixture
async def refresh_token_val(db_session, regular_user):
    """Создаёт refresh token для regular_user напрямую в БД."""
    service = UserService(db_session)
    return await service.create_refresh_token(REGULAR_USER_ID)


# ── Фикстуры токенов ──────────────────────────────────────────────────────────
# Токен — просто подписанный JWT. Создаётся без обращения к БД.

@pytest.fixture
def regular_token():
    return create_access_token({
        "sub": str(REGULAR_USER_ID),
        "email": "employee@test.com",
        "roles": ["Сотрудник"],
        "is_active": True,
    })


@pytest.fixture
def manager_token():
    return create_access_token({
        "sub": str(MANAGER_USER_ID),
        "email": "manager@test.com",
        "roles": ["Менеджер", "Сотрудник"],
        "is_active": True,
    })
