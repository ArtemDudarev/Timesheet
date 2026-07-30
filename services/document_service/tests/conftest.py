import time
import uuid
import pytest
import pytest_asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from jose import jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.models.base import Base
from src.models.document_type import DocumentType
from src.models.employee import Employee
from src.database import get_async_session
from src.main import app
from src.storage import storage

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
JWT_SECRET = "change-me-in-production"
JWT_ALGORITHM = "HS256"

# ── Фиксированные UUID ────────────────────────────────────────────────────────
AUTHOR_ID   = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
SIGNER_ID   = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000002")
APPROVER_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000003")
OUTSIDER_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000004")
CONTRACT_TYPE_ID = uuid.UUID("00000000-0000-0000-0006-000000000001")


def create_test_token(sub: str, permissions: list[str] | None = None) -> str:
    return jwt.encode(
        {
            "sub": sub,
            "roles": ["Сотрудник"],
            "permissions": permissions if permissions is not None else [],
            "is_active": True,
            "exp": int(time.time()) + 3600,
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


# ── Инфраструктурные фикстуры ─────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def tmp_storage(tmp_path):
    """Файлы тестов — во временный каталог, не в /data/files."""
    original = storage.root
    storage.root = Path(tmp_path)
    yield
    storage.root = original


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
        patch("src.main.seed_document_types", new_callable=AsyncMock),
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
async def contract_type(db_session):
    t = DocumentType(id=CONTRACT_TYPE_ID, code="CONTRACT", name="Договор", color="#3B82F6")
    db_session.add(t)
    await db_session.flush()
    return t


@pytest_asyncio.fixture
async def test_employees(db_session):
    employees = [
        Employee(id=AUTHOR_ID, first_name="Иван", last_name="Автор"),
        Employee(id=SIGNER_ID, first_name="Пётр", last_name="Подписант"),
        Employee(id=APPROVER_ID, first_name="Анна", last_name="Согласующая"),
        Employee(id=OUTSIDER_ID, first_name="Олег", last_name="Чужой"),
    ]
    db_session.add_all(employees)
    await db_session.flush()
    return employees


# ── Токены ────────────────────────────────────────────────────────────────────

@pytest.fixture
def author_token():
    return create_test_token(str(AUTHOR_ID))


@pytest.fixture
def signer_token():
    return create_test_token(str(SIGNER_ID))


@pytest.fixture
def approver_token():
    return create_test_token(str(APPROVER_ID))


@pytest.fixture
def outsider_token():
    return create_test_token(str(OUTSIDER_ID))


@pytest.fixture
def admin_token():
    return create_test_token(
        str(uuid.uuid4()), ["document:read_any", "document:manage_templates"]
    )
