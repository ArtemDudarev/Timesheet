import time
import uuid
import pytest
import pytest_asyncio
from datetime import date
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from jose import jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.models.base import Base
from src.models.department import Department
from src.models.department_plan import DepartmentPlan
from src.models.employee import Employee
from src.models.project import Project
from src.models.time_entry_replica import TimeEntryReplica
from src.database import get_async_session
from src.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
JWT_SECRET = "change-me-in-production"
JWT_ALGORITHM = "HS256"

# ── Фиксированные UUID ────────────────────────────────────────────────────────
DEPARTMENT_ID = uuid.UUID("11111111-0000-0000-0000-000000000001")
EMPLOYEE_ID   = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
EMPLOYEE_2_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000002")
PROJECT_ID    = uuid.UUID("33333333-0000-0000-0000-000000000001")
PLAN_ID       = uuid.UUID("44444444-0000-0000-0000-000000000001")


def create_test_token(sub: str, permissions: list[str]) -> str:
    return jwt.encode(
        {
            "sub": sub,
            "roles": ["Менеджер"],
            "permissions": permissions,
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
async def test_department(db_session):
    dept = Department(id=DEPARTMENT_ID, name="Разработка")
    db_session.add(dept)
    await db_session.flush()
    return dept


@pytest_asyncio.fixture
async def test_employees(db_session, test_department):
    employees = [
        Employee(id=EMPLOYEE_ID, first_name="Иван", last_name="Петров", department_id=DEPARTMENT_ID),
        Employee(id=EMPLOYEE_2_ID, first_name="Анна", last_name="Смирнова", department_id=DEPARTMENT_ID),
    ]
    db_session.add_all(employees)
    await db_session.flush()
    return employees


@pytest_asyncio.fixture
async def test_project(db_session):
    project = Project(
        id=PROJECT_ID,
        name="Омниканальная платформа",
        client="ООО Ритейл",
        status="Активный",
        budget_hours=100,
        deadline=date(2026, 12, 31),
    )
    db_session.add(project)
    await db_session.flush()
    return project


@pytest_asyncio.fixture
async def test_entries(db_session, test_employees, test_project):
    """Июнь 2026: Иван 16ч WORK на проекте, Анна 8ч WORK без проекта + 8ч SICK_LEAVE."""
    entries = [
        TimeEntryReplica(
            entry_id=uuid.uuid4(), period_id=uuid.uuid4(), employee_id=EMPLOYEE_ID,
            project_id=PROJECT_ID, type_code="WORK",
            date_from=date(2026, 6, 1), date_to=date(2026, 6, 1),
            spend_time=8, year=2026, month=6,
        ),
        TimeEntryReplica(
            entry_id=uuid.uuid4(), period_id=uuid.uuid4(), employee_id=EMPLOYEE_ID,
            project_id=PROJECT_ID, type_code="WORK",
            date_from=date(2026, 6, 2), date_to=date(2026, 6, 2),
            spend_time=8, year=2026, month=6,
        ),
        TimeEntryReplica(
            entry_id=uuid.uuid4(), period_id=uuid.uuid4(), employee_id=EMPLOYEE_2_ID,
            project_id=None, type_code="WORK",
            date_from=date(2026, 6, 1), date_to=date(2026, 6, 1),
            spend_time=8, year=2026, month=6,
        ),
        TimeEntryReplica(
            entry_id=uuid.uuid4(), period_id=uuid.uuid4(), employee_id=EMPLOYEE_2_ID,
            project_id=None, type_code="SICK_LEAVE",
            date_from=date(2026, 6, 2), date_to=date(2026, 6, 2),
            spend_time=8, year=2026, month=6,
        ),
    ]
    db_session.add_all(entries)
    await db_session.flush()
    return entries


@pytest_asyncio.fixture
async def test_plan(db_session, test_department):
    plan = DepartmentPlan(
        id=PLAN_ID, department_id=DEPARTMENT_ID, year=2026, month=6, planned_hours=160,
    )
    db_session.add(plan)
    await db_session.flush()
    return plan


# ── Токены ────────────────────────────────────────────────────────────────────

@pytest.fixture
def reader_token():
    return create_test_token(str(uuid.uuid4()), ["report:read"])


@pytest.fixture
def manager_token():
    return create_test_token(str(uuid.uuid4()), ["report:read", "report:manage"])


@pytest.fixture
def employee_token():
    return create_test_token(str(uuid.uuid4()), [])
