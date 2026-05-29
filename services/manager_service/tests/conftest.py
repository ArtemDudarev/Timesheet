import time
import uuid
import pytest
import pytest_asyncio
from datetime import date
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from jose import jwt
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from sqlalchemy import text

from src.models.base import Base
from src.models.status import Status
from src.models.role import Role
from src.models.user import User
from src.models.user_role import user_role
from src.models.employee import Employee
from src.models.project import Project, ProjectStatus
from src.models.project_role import ProjectRole
from src.models.employee_project import EmployeeProject, AssignmentStatus
from src.database import get_async_session
from src.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
JWT_SECRET = "change-me-in-production"
JWT_ALGORITHM = "HS256"

# ── Фиксированные UUID ────────────────────────────────────────────────────────
MANAGER_ROLE_ID  = uuid.UUID("00000000-0000-0000-0000-000000000001")
EMPLOYEE_ROLE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
STATUS_ID        = uuid.UUID("11111111-0000-0000-0000-000000000001")
STATUS_2_ID      = uuid.UUID("11111111-0000-0000-0000-000000000002")
PROJECT_ROLE_ID  = uuid.UUID("22222222-0000-0000-0000-000000000001")
PROJECT_ID       = uuid.UUID("33333333-0000-0000-0000-000000000001")
EMPLOYEE_ID      = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
MANAGER_USER_ID  = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000002")


def create_test_token(sub: str, roles: list[str]) -> str:
    return jwt.encode(
        {"sub": sub, "roles": roles, "is_active": True, "exp": int(time.time()) + 3600},
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
        patch("src.main.seed_roles", new_callable=AsyncMock),
        patch("src.main.seed_statuses", new_callable=AsyncMock),
        patch("src.main.seed_project_roles", new_callable=AsyncMock),
        patch("src.main.seed_demo_projects", new_callable=AsyncMock),
        patch("src.main.seed_demo_employee_profiles", new_callable=AsyncMock),
        patch("src.main.seed_demo_assignments", new_callable=AsyncMock),
        patch("src.main.seed_demo_employee_statuses", new_callable=AsyncMock),
        patch("src.main.asyncio.sleep", new_callable=AsyncMock),
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
async def test_status(db_session):
    status = Status(id=STATUS_ID, name="Новый", description="Начальный статус")
    db_session.add(status)
    await db_session.flush()
    return status


@pytest_asyncio.fixture
async def test_status_2(db_session):
    status = Status(id=STATUS_2_ID, name="Активный", description="Активный статус")
    db_session.add(status)
    await db_session.flush()
    return status


@pytest_asyncio.fixture
async def manager_role(db_session):
    role = Role(id=MANAGER_ROLE_ID, name="Менеджер", description="Управляющая роль")
    db_session.add(role)
    await db_session.flush()
    return role


@pytest_asyncio.fixture
async def employee_role(db_session):
    role = Role(id=EMPLOYEE_ROLE_ID, name="Сотрудник", description="Базовая роль")
    db_session.add(role)
    await db_session.flush()
    return role


@pytest_asyncio.fixture
async def test_project_role(db_session):
    pr = ProjectRole(id=PROJECT_ROLE_ID, name="Разработчик", description="Backend")
    db_session.add(pr)
    await db_session.flush()
    return pr


@pytest_asyncio.fixture
async def test_project(db_session):
    project = Project(id=PROJECT_ID, name="Тестовый проект", status=ProjectStatus.ACTIVE)
    db_session.add(project)
    await db_session.flush()
    return project


@pytest_asyncio.fixture
async def test_employee(db_session, test_status, employee_role):
    user = User(
        id=EMPLOYEE_ID,
        email="employee@test.com",
        number="EMP-100001",
        is_active=True,
        register_date=date.today(),
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.execute(
        insert(user_role).values(user_id=EMPLOYEE_ID, role_id=EMPLOYEE_ROLE_ID)
    )
    employee = Employee(id=EMPLOYEE_ID, first_name="Иван", last_name="Петров", status_id=STATUS_ID)
    db_session.add(employee)
    await db_session.flush()
    return employee


@pytest_asyncio.fixture
async def test_assignment(db_session, test_employee, test_project, test_project_role):
    assignment = EmployeeProject(
        employee_id=EMPLOYEE_ID,
        project_id=PROJECT_ID,
        project_role_id=PROJECT_ROLE_ID,
        status=AssignmentStatus.ACTIVE,
    )
    db_session.add(assignment)
    await db_session.flush()
    return assignment


# ── Токены ────────────────────────────────────────────────────────────────────

@pytest.fixture
def manager_token():
    return create_test_token(str(MANAGER_USER_ID), ["Менеджер", "Сотрудник"])


@pytest.fixture
def employee_token():
    return create_test_token(str(EMPLOYEE_ID), ["Сотрудник"])
