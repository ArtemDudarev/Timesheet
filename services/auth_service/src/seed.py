import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.role import Role

ROLE_SOTRUDNIK_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ROLE_MANAGER_ID   = uuid.UUID("00000000-0000-0000-0000-000000000002")

SEED_ROLES = [
    {"id": ROLE_SOTRUDNIK_ID, "name": "Сотрудник", "description": "Базовая роль для всех сотрудников"},
    {"id": ROLE_MANAGER_ID,   "name": "Менеджер",  "description": "Роль с правами управления"},
]


async def seed_roles(session_maker: async_sessionmaker[AsyncSession]) -> None:
    async with session_maker() as session:
        for role_data in SEED_ROLES:
            result = await session.execute(
                select(Role).where(Role.name == role_data["name"])
            )
            if result.scalar_one_or_none() is None:
                session.add(Role(
                    id=role_data["id"],
                    name=role_data["name"],
                    description=role_data["description"],
                ))
        await session.commit()
