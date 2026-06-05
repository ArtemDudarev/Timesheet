from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user
from src.models.department import Department
from src.schemas.department import DepartmentRead

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("/", response_model=list[DepartmentRead])
async def list_departments(
    session: AsyncSession = Depends(get_async_session),
    _: dict = Depends(get_current_user),
):
    result = await session.execute(select(Department).order_by(Department.name))
    return result.scalars().all()
