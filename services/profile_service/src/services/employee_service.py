import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.employee import Employee
from src.schemas.employee import EmployeeUpdate


class EmployeeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_employee_full_by_id(self, employee_id: uuid.UUID) -> Optional[Employee]:
        result = await self.db.execute(
            select(Employee).where(Employee.id == employee_id)
        )
        return result.scalar_one_or_none()

    async def update_employee_profile(
        self,
        employee: Employee,
        employee_in: EmployeeUpdate,
    ) -> Employee:
        update_data = employee_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(employee, field, value)

        try:
            await self.db.commit()
            await self.db.refresh(
                employee,
                attribute_names=["roles", "status", "assignments"],
            )
            return employee
        except IntegrityError as exc:
            await self.db.rollback()
            self._raise_employee_integrity_error(exc, employee.email, employee.number)

    def _raise_employee_integrity_error(
        self,
        exc: IntegrityError,
        email: str,
        number: str | None,
    ) -> None:
        error_msg = str(exc.orig).lower()

        if "email" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{email}' уже зарегистрирован",
            )

        if "number" in error_msg and number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Номер сотрудника '{number}' уже зарегистрирован",
            )

        if "status" in error_msg or "foreign key" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Некорректный статус сотрудника или связанные данные",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Данные сотрудника конфликтуют с существующими записями",
        )
