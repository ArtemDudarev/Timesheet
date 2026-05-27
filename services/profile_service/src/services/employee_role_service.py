import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.employee_role import employee_role


class EmployeeRoleService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_employee_id(self, employee_id: uuid.UUID) -> list[dict]:
        result = await self.session.execute(
            select(employee_role).where(
                employee_role.c.employee_id == employee_id
            )
        )
        return [dict(row) for row in result.mappings().all()]

