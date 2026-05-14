import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.employee_role import EmployeeRole


class EmployeeRoleService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, employee_role_id: uuid.UUID) -> EmployeeRole | None:
        result = await self.session.execute(
            select(EmployeeRole).where(
                EmployeeRole.id == employee_role_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_employee_id(self, employee_id: uuid.UUID) -> list[EmployeeRole]:
        result = await self.session.execute(
            select(EmployeeRole).where(
                EmployeeRole.employee_id == employee_id
            )
        )
        return list(result.scalars().all())

    async def get_by_role_id(self, role_id: uuid.UUID) -> list[EmployeeRole]:
        result = await self.session.execute(
            select(EmployeeRole).where(
                EmployeeRole.role_id == role_id
            )
        )
        return list(result.scalars().all())
