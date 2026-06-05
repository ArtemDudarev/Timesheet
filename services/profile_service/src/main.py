import asyncio
import uuid
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from .database import engine, async_session_maker
from .kafka.consumer import KafkaEventConsumer
from .kafka.producer import KafkaEventProducer
from .models.base import Base

# Импортируем ВСЕ модели для регистрации метаданных
from .models.status import Status
from .models.role import Role
from .models.project_status import ProjectStatus
from .models.assignment_status import AssignmentStatus
from .models.project import Project
from .models.user import User
from .models.user_role import user_role
from .models.employee import Employee
from .models.project_role import ProjectRole
from .models.employee_project import Assignment
from .models.department import Department
from .models.grade import Grade
from .models.skill import Skill, employee_skill

from .routers.status import router as status_router
from .routers.employee import router as employee_router
from .routers.employee_role import router as employee_role_router
from .routers.department import router as department_router
from .routers.grade import router as grade_router
from .routers.skill import router as skill_router

_PROJECT_STATUSES = [
    (uuid.UUID("00000000-0000-0000-0001-000000000001"), "PLANNED",   "Планируется"),
    (uuid.UUID("00000000-0000-0000-0001-000000000002"), "ACTIVE",    "Активный"),
    (uuid.UUID("00000000-0000-0000-0001-000000000003"), "ON_HOLD",   "Приостановлен"),
    (uuid.UUID("00000000-0000-0000-0001-000000000004"), "COMPLETED", "Завершён"),
    (uuid.UUID("00000000-0000-0000-0001-000000000005"), "ARCHIVED",  "Архивный"),
]

_ASSIGNMENT_STATUSES = [
    (uuid.UUID("00000000-0000-0000-0002-000000000001"), "REQUEST",  "Заявка"),
    (uuid.UUID("00000000-0000-0000-0002-000000000002"), "ACTIVE",   "Привлечён"),
    (uuid.UUID("00000000-0000-0000-0002-000000000003"), "EXTENDED", "Продлён"),
    (uuid.UUID("00000000-0000-0000-0002-000000000004"), "REMOVED",  "Снят с проекта"),
]


async def _seed_ref_tables() -> None:
    async with async_session_maker() as session:
        for sid, code, name in _PROJECT_STATUSES:
            if await session.get(ProjectStatus, sid) is None:
                session.add(ProjectStatus(id=sid, code=code, name=name))
        for sid, code, name in _ASSIGNMENT_STATUSES:
            if await session.get(AssignmentStatus, sid) is None:
                session.add(AssignmentStatus(id=sid, code=code, name=name))
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_ref_tables()
    app.state.kafka_producer = KafkaEventProducer()
    await app.state.kafka_producer.start()
    app.state.kafka_consumer = KafkaEventConsumer()
    app.state.kafka_consumer_task = asyncio.create_task(
        app.state.kafka_consumer.start()
    )
    yield
    await app.state.kafka_producer.stop()
    app.state.kafka_consumer_task.cancel()
    await app.state.kafka_consumer.stop()
    with suppress(asyncio.CancelledError):
        await app.state.kafka_consumer_task
    await engine.dispose()

app = FastAPI(title="Profile Service", lifespan=lifespan)

app.include_router(status_router)
app.include_router(employee_router)
app.include_router(employee_role_router)
app.include_router(department_router)
app.include_router(grade_router)
app.include_router(skill_router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "profile_service"}
