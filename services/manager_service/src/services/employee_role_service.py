import uuid

from fastapi import HTTPException, status
from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.employee import Employee
from src.models.employee_role import employee_role
from src.models.role import Role


class EmployeeRoleService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def employee_exists(self, employee_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(Employee.id).where(Employee.id == employee_id)
        )
        return result.scalar_one_or_none() is not None

    async def get_existing_role_ids(self, role_ids: list[uuid.UUID]) -> set[uuid.UUID]:
        if not role_ids:
            return set()

        result = await self.session.execute(
            select(Role.id).where(Role.id.in_(role_ids))
        )
        return set(result.scalars().all())

    async def get_by_employee_id(self, employee_id: uuid.UUID) -> list[dict]:
        result = await self.session.execute(
            select(employee_role).where(
                employee_role.c.employee_id == employee_id
            )
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_by_role_id(self, role_id: uuid.UUID) -> list[dict]:
        result = await self.session.execute(
            select(employee_role).where(
                employee_role.c.role_id == role_id
            )
        )
        return [dict(row) for row in result.mappings().all()]

    async def add_roles_to_employee(
        self,
        employee_id: uuid.UUID,
        role_ids: list[uuid.UUID],
    ) -> list[dict]:
        role_ids = list(dict.fromkeys(role_ids))
        current_roles = await self.get_by_employee_id(employee_id)
        current_role_ids = {row["role_id"] for row in current_roles}
        new_role_ids = [role_id for role_id in role_ids if role_id not in current_role_ids]

        if not new_role_ids:
            return current_roles

        try:
            await self.session.execute(
                insert(employee_role),
                [
                    {"employee_id": employee_id, "role_id": role_id}
                    for role_id in new_role_ids
                ],
            )
            await self.session.commit()
            return await self.get_by_employee_id(employee_id)
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Данные связи сотрудника и роли конфликтуют с существующими записями",
            )

    async def replace_employee_roles(
        self,
        employee_id: uuid.UUID,
        role_ids: list[uuid.UUID],
    ) -> list[dict]:
        role_ids = list(dict.fromkeys(role_ids))

        try:
            await self.session.execute(
                delete(employee_role).where(employee_role.c.employee_id == employee_id)
            )

            if role_ids:
                await self.session.execute(
                    insert(employee_role),
                    [
                        {"employee_id": employee_id, "role_id": role_id}
                        for role_id in role_ids
                    ],
                )

            await self.session.commit()
            return await self.get_by_employee_id(employee_id)
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Данные связи сотрудника и роли конфликтуют с существующими записями",
            )
