import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.absence_type import AbsenceType

SEED_ABSENCE_TYPES = [
    {"id": uuid.UUID("00000000-0000-0000-0005-000000000001"), "code": "VACATION", "name": "Отпуск",       "color": "#3B82F6", "requires_approval": True},
    {"id": uuid.UUID("00000000-0000-0000-0005-000000000002"), "code": "SICK",     "name": "Больничный",   "color": "#F59E0B", "requires_approval": True},
    {"id": uuid.UUID("00000000-0000-0000-0005-000000000003"), "code": "TRIP",     "name": "Командировка", "color": "#8B5CF6", "requires_approval": True},
    {"id": uuid.UUID("00000000-0000-0000-0005-000000000004"), "code": "DAY_OFF",  "name": "Отгул",        "color": "#10B981", "requires_approval": True},
]


async def seed_absence_types(session_maker: async_sessionmaker[AsyncSession]) -> None:
    async with session_maker() as session:
        for type_data in SEED_ABSENCE_TYPES:
            result = await session.execute(
                select(AbsenceType).where(AbsenceType.code == type_data["code"])
            )
            existing = result.scalar_one_or_none()
            if existing is None:
                session.add(AbsenceType(**type_data))
            else:
                existing.name = type_data["name"]
                existing.color = type_data["color"]
                existing.requires_approval = type_data["requires_approval"]
        await session.commit()
