from fastapi import FastAPI
from contextlib import asynccontextmanager

from .database import engine
from .models.base import Base

# Импортируем модели, чтобы Base.metadata их увидел
from .models.status import Status
from .models.role import Role
from .models.employee_role import employee_role

from .routers.status import router as status_router
from .routers.role import router as role_router
from .routers.employee_role import router as employee_role_router
from .routers.employee import router as employee_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # При старте: создаем таблицы, если их нет
    async with engine.begin() as conn:
        # Важно: чтобы это сработало, модели должны быть импортированы!
        await conn.run_sync(Base.metadata.create_all)

    yield  # Здесь приложение работает

    # При выключении: закрываем соединения
    await engine.dispose()


app = FastAPI(title="Profile Service", lifespan=lifespan)

app.include_router(status_router)
app.include_router(role_router)
app.include_router(employee_role_router)
app.include_router(employee_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "profile_service"}
