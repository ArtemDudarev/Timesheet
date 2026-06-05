from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user
from src.models.grade import Grade
from src.schemas.grade import GradeRead

router = APIRouter(prefix="/grades", tags=["Grades"])


@router.get("/", response_model=list[GradeRead])
async def list_grades(
    session: AsyncSession = Depends(get_async_session),
    _: dict = Depends(get_current_user),
):
    result = await session.execute(select(Grade).order_by(Grade.sort_order, Grade.name))
    return result.scalars().all()
