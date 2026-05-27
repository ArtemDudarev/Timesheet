import uuid
from typing import List, Optional, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.employee import Employee
from src.models.role import Role
from src.models.status import Status


ModelT = TypeVar("ModelT")


class EmployeeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_with_related(self, skip: int = 0, limit: int = 100) -> List[Employee]:
        result = await self.db.execute(
            select(Employee).offset(skip).limit(limit).order_by(Employee.id)
        )
        return list(result.scalars().all())

    async def get_employee_by_id(self, employee_id: uuid.UUID) -> Optional[Employee]:
        result = await self.db.execute(
            select(Employee).where(Employee.id == employee_id)
        )
        return result.scalar_one_or_none()

    async def update_employee_roles(
        self,
        employee: Employee,
        role_ids: list[uuid.UUID],
    ) -> Employee:
        employee.roles = await self._get_entities_by_ids_or_raise(
            Role,
            role_ids,
            "Одна или несколько ролей не найдены",
        )
        return await self._commit_employee_update(employee)

    async def update_employee_status(
        self,
        employee: Employee,
        status_id: uuid.UUID,
    ) -> Employee:
        db_status = await self.db.get(Status, status_id)
        if not db_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Статус не найден",
            )

        employee.status_id = status_id
        return await self._commit_employee_update(employee)

    async def _get_entities_by_ids_or_raise(
        self,
        model: type[ModelT],
        entity_ids: list[uuid.UUID],
        detail: str,
    ) -> list[ModelT]:
        entity_ids = list(dict.fromkeys(entity_ids))
        if not entity_ids:
            return []

        result = await self.db.execute(
            select(model).where(model.id.in_(entity_ids))
        )
        entities = list(result.scalars().all())

        if len(entities) != len(entity_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            )

        return entities

    async def _commit_employee_update(self, employee: Employee) -> Employee:
        try:
            await self.db.commit()
            await self.db.refresh(
                employee,
                attribute_names=["roles", "status", "assignments"],
            )
            return employee
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Данные сотрудника конфликтуют с существующими записями",
            )
