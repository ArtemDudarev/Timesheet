from contextlib import asynccontextmanager
from fastapi import FastAPI

from .database import engine
from src.models.base import Base
from src.models.employee import Employee
from src.models.role import Role
from src.routers.employee import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "Auth Service is running"}

app.include_router(auth_router)