import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import require_permission
from src.schemas.department_plan import (
    DepartmentPlanCreate,
    DepartmentPlanRead,
    DepartmentPlanUpdate,
)
from src.services.department_plan_service import DepartmentPlanService

router = APIRouter(prefix="/department-plans", tags=["Department Plans"])

_manager = Depends(require_permission("report:manage"))


@router.get("/", response_model=list[DepartmentPlanRead])
async def get_plans(
    year: int | None = None,
    month: int | None = None,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    return await DepartmentPlanService(session).get_all(
        year=year, month=month, skip=skip, limit=limit
    )


@router.post("/", response_model=DepartmentPlanRead, status_code=status.HTTP_201_CREATED)
async def create_plan(
    data: DepartmentPlanCreate,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    plan = await DepartmentPlanService(session).create(data)
    await session.commit()
    return plan


@router.patch("/{plan_id}", response_model=DepartmentPlanRead)
async def update_plan(
    plan_id: uuid.UUID,
    data: DepartmentPlanUpdate,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    plan = await DepartmentPlanService(session).update(plan_id, data)
    await session.commit()
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    await DepartmentPlanService(session).delete(plan_id)
    await session.commit()
