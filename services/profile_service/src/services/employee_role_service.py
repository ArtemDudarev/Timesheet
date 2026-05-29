import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user_role import user_role


class EmployeeRoleService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_employee_id(self, employee_id: uuid.UUID) -> list[dict]:
        result = await self.session.execute(
            select(user_role).where(
                user_role.c.user_id == employee_id
            )
        )
        return [
            {"employee_id": row["user_id"], "role_id": row["role_id"]}
            for row in result.mappings().all()
        ]

