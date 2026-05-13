from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models.status import Status
from ..schemas.status import StatusCreate

async def get_all_statuses(session: AsyncSession):
    result = await session.execute(select(Status))
    return result.scalars().all()

async def create_status(session: AsyncSession, status_data: StatusCreate):
    new_status = Status(**status_data.model_dump())
    session.add(new_status)
    await session.commit()
    await session.refresh(new_status)
    return new_status