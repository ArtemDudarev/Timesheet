import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from .database import engine
from .kafka.consumer import KafkaEventConsumer
from .kafka.producer import KafkaEventProducer
from .models.base import Base

# Импортируем ВСЕ модели для регистрации метаданных
from .models.status import Status
from .models.role import Role
from .models.project import Project  # Добавлен импорт проекта
from .models.employee import Employee
from .models.employee_role import employee_role
from .models.project_role import ProjectRole
from .models.employee_project import EmployeeProject

from .routers.status import router as status_router
from .routers.employee_role import router as employee_role_router
from .routers.employee import router as employee_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
app.include_router(employee_role_router)
app.include_router(employee_router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "profile_service"}
