import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Подтягиваем переменные, которые Docker передаст в контейнер
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_NAME = "auth_db"  # Название базы из вашего compose
DB_HOST = "auth_db"  # Имя сервиса/контейнера из вашего compose
DB_PORT = "5432"     # Внутри сети Docker всегда стандартный порт 5432

# Собираем строку подключения для asyncpg
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Создаем асинхронный движок
engine = create_async_engine(
    DATABASE_URL,
    echo=True, # Включаем логирование SQL-запросов для отладки
)

# Фабрика для создания сессий
async_session_maker = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Генератор сессий для FastAPI (Dependency Injection)
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session