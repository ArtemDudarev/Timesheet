from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.database import engine
from src.models.base import Base

# ВАЖНО: Импортируем все модели, чтобы Base.metadata их "увидел"
from src.models.employee import Employee
from src.models.role import Role

from src.routers.employee import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Теперь, благодаря импортам выше, Base.metadata содержит и Employee, и Role
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "Auth Service is running"}

app.include_router(auth_router)