import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.document_type import DocumentType

SEED_DOCUMENT_TYPES = [
    {"id": uuid.UUID("00000000-0000-0000-0006-000000000001"), "code": "CONTRACT",  "name": "Договор",   "color": "#3B82F6", "icon": "file-text"},
    {"id": uuid.UUID("00000000-0000-0000-0006-000000000002"), "code": "ORDER",     "name": "Приказ",    "color": "#8B5CF6", "icon": "file-badge"},
    {"id": uuid.UUID("00000000-0000-0000-0006-000000000003"), "code": "STATEMENT", "name": "Заявление", "color": "#10B981", "icon": "file-pen"},
    {"id": uuid.UUID("00000000-0000-0000-0006-000000000004"), "code": "ACT",       "name": "Акт",       "color": "#F59E0B", "icon": "file-check"},
]


async def seed_document_types(session_maker: async_sessionmaker[AsyncSession]) -> None:
    async with session_maker() as session:
        for type_data in SEED_DOCUMENT_TYPES:
            result = await session.execute(
                select(DocumentType).where(DocumentType.code == type_data["code"])
            )
            existing = result.scalar_one_or_none()
            if existing is None:
                session.add(DocumentType(**type_data))
            else:
                existing.name = type_data["name"]
                existing.color = type_data["color"]
                existing.icon = type_data["icon"]
        await session.commit()
