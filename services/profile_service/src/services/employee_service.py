from datetime import date
import uuid
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.employee import Employee
from src.models.role import Role
from src.schemas.employee import EmployeeCreate, EmployeeUpdate


class EmployeeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_employee(self, employee_in: EmployeeCreate) -> Employee:
        roles_list = await self._get_roles_or_raise(employee_in.role_ids)

        employee = Employee(
            first_name=employee_in.first_name,
            last_name=employee_in.last_name,
            email=employee_in.email,
            hashed_password=employee_in.password,
            number=employee_in.number,
            phone=employee_in.phone,
            address=employee_in.address,
            birthday=employee_in.birthday,
            status_id=employee_in.status_id,
            register_date=date.today(),
            roles=roles_list,
        )

        try:
            self.db.add(employee)
            await self.db.commit()
            await self.db.refresh(employee, attribute_names=["roles"])
            return employee
        except IntegrityError as exc:
            await self.db.rollback()
            self._raise_employee_integrity_error(exc, employee_in.email, employee_in.number)

    async def get_employee_by_id(self, employee_id: uuid.UUID) -> Optional[Employee]:
        result = await self.db.execute(
            select(Employee).where(Employee.id == employee_id)
        )
        return result.scalar_one_or_none()

    async def get_employee_by_email(self, email: str) -> Optional[Employee]:
        result = await self.db.execute(
            select(Employee).where(Employee.email == email)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Employee]:
        result = await self.db.execute(
            select(Employee).offset(skip).limit(limit).order_by(Employee.id)
        )
        return result.scalars().all()

    async def update_employee(self, employee: Employee, employee_in: EmployeeUpdate) -> Employee:
        update_data = employee_in.model_dump(exclude_unset=True)
        role_ids = update_data.pop("role_ids", None)

        for field, value in update_data.items():
            setattr(employee, field, value)

        if role_ids is not None:
            employee.roles = await self._get_roles_or_raise(role_ids)

        try:
            await self.db.commit()
            await self.db.refresh(employee, attribute_names=["roles"])
            return employee
        except IntegrityError as exc:
            await self.db.rollback()
            self._raise_employee_integrity_error(exc, employee.email, employee.number)

    async def _get_roles_or_raise(self, role_ids: list[uuid.UUID]) -> list[Role]:
        role_ids = list(dict.fromkeys(role_ids))
        if not role_ids:
            return []

        roles_query = select(Role).where(Role.id.in_(role_ids))
        roles_result = await self.db.execute(roles_query)
        roles_list = list(roles_result.scalars().all())

        if len(roles_list) != len(role_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Одна или несколько ролей не найдены",
            )

        return roles_list

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
