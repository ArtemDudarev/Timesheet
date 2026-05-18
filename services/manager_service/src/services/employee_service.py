import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.employee import Employee


class EmployeeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Employee]:
        result = await self.db.execute(
            select(Employee).offset(skip).limit(limit).order_by(Employee.id)
        )
        return result.scalars().all()

    async def get_employee_by_id(self, employee_id: uuid.UUID) -> Optional[Employee]:
        result = await self.db.execute(
            select(Employee).where(Employee.id == employee_id)
        )
        return result.scalar_one_or_none()
