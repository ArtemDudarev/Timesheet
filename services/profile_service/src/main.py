from fastapi import FastAPI
from contextlib import asynccontextmanager
from .database import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # При старте: создаем таблицы, если их нет
    async with engine.begin() as conn:
        # Важно: чтобы это сработало, модели должны быть импортированы!
        await conn.run_sync(Base.metadata.create_all)
    
    yield # Здесь приложение работает
    
    # При выключении: закрываем соединения
    await engine.dispose()

app = FastAPI(title="Profile Service", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "profile_service"}