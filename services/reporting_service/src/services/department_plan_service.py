import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.department import Department
from src.models.department_plan import DepartmentPlan
from src.schemas.department_plan import DepartmentPlanCreate, DepartmentPlanUpdate


class DepartmentPlanService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        year: int | None = None,
        month: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DepartmentPlan]:
        q = select(DepartmentPlan)
        if year is not None:
            q = q.where(DepartmentPlan.year == year)
        if month is not None:
            q = q.where(DepartmentPlan.month == month)
        q = q.order_by(DepartmentPlan.year.desc(), DepartmentPlan.month.desc())
        q = q.offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, plan_id: uuid.UUID) -> DepartmentPlan | None:
        return await self.db.get(DepartmentPlan, plan_id)

    async def create(self, data: DepartmentPlanCreate) -> DepartmentPlan:
        department = await self.db.get(Department, data.department_id)
        if department is None:
            raise HTTPException(status_code=404, detail="Отдел не найден")
        plan = DepartmentPlan(
            department_id=data.department_id,
            year=data.year,
            month=data.month,
            planned_hours=data.planned_hours,
        )
        try:
            self.db.add(plan)
            await self.db.flush()
            return plan
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="План для этого отдела на этот месяц уже существует",
            )

    async def update(self, plan_id: uuid.UUID, data: DepartmentPlanUpdate) -> DepartmentPlan:
        plan = await self.get_by_id(plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="План не найден")
        if data.planned_hours is not None:
            plan.planned_hours = data.planned_hours
        await self.db.flush()
        return plan

    async def delete(self, plan_id: uuid.UUID) -> None:
        plan = await self.get_by_id(plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="План не найден")
        await self.db.delete(plan)
        await self.db.flush()
