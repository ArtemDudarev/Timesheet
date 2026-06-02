import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from .database import engine, async_session_maker
from .kafka.consumer import KafkaEventConsumer
from .kafka.producer import KafkaEventProducer
from .models.base import Base
from .seed import (
    seed_assignment_statuses,
    seed_demo_assignments,
    seed_demo_employee_profiles,
    seed_demo_employee_statuses,
    seed_demo_projects,
    seed_project_roles,
    seed_project_statuses,
    seed_roles,
    seed_statuses,
)

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
from .models.employee_project import EmployeeProject

from .routers.status import router as status_router
from .routers.project import router as project_router
from .routers.project_status import router as project_status_router
from .routers.assignment_status import router as assignment_status_router
from .routers.role import router as role_router
from .routers.project_role import router as project_role_router
from .routers.employee import router as employee_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.kafka_producer = KafkaEventProducer()
    await app.state.kafka_producer.start()
    await seed_project_statuses(async_session_maker)
    await seed_assignment_statuses(async_session_maker)
    await seed_roles(async_session_maker, app.state.kafka_producer)
    await seed_statuses(async_session_maker, app.state.kafka_producer)
    await seed_project_roles(async_session_maker, app.state.kafka_producer)
    await seed_demo_projects(async_session_maker, app.state.kafka_producer)
    await seed_demo_employee_profiles(async_session_maker, app.state.kafka_producer)
    await asyncio.sleep(8)
    await seed_demo_assignments(async_session_maker, app.state.kafka_producer)
    await seed_demo_employee_statuses(async_session_maker, app.state.kafka_producer)
    app.state.kafka_consumer = KafkaEventConsumer(producer=app.state.kafka_producer)
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

app = FastAPI(title="Manager Service", lifespan=lifespan)

app.include_router(status_router)
app.include_router(project_status_router)
app.include_router(assignment_status_router)
app.include_router(project_router)
app.include_router(role_router)
app.include_router(project_role_router)
app.include_router(employee_router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "manager_service"}
