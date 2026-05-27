from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.models.status import Status


async def get_all_statuses(session: AsyncSession):
    result = await session.execute(select(Status))
    return result.scalars().all()
