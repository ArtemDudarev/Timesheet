from datetime import date
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.employee import Employee
from src.models.role import Role
from src.schemas.employee import EmployeeCreate, EmployeeUpdate
from typing import List, Optional

class EmployeeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_employee(self, employee_in: EmployeeCreate) -> Employee:
        # Получаем объекты ролей по переданным UUID
        roles_list = []
        if employee_in.role_ids:
            roles_query = select(Role).where(Role.id.in_(employee_in.role_ids))
            roles_result = await self.db.execute(roles_query)
            roles_list = roles_result.scalars().all()

        employee = Employee(
            first_name=employee_in.first_name,
            last_name=employee_in.last_name,
            email=employee_in.email,
            hashed_password=employee_in.password,  # в реальном сервисе здесь хэш!
            number=employee_in.number,
            phone=employee_in.phone,
            address=employee_in.address,
            birthday=employee_in.birthday,
            status_id=employee_in.status_id,
            register_date=date.today(),
            roles=roles_list
        )
        self.db.add(employee)
        await self.db.commit()
        await self.db.refresh(employee, attribute_names=["roles"])
        return employee

    async def get_employee_by_id(self, employee_id: uuid.UUID) -> Optional[Employee]:  # ИСПРАВЛЕНО: UUID
        result = await self.db.execute(
            select(Employee).where(Employee.id == employee_id)
        )
        return result.scalar_one_or_none()

    async def get_employee_by_email(self, email: str) -> Optional[Employee]:
        result = await self.db.execute(
            select(Employee).where(Employee.email == email)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Employee]:  # Синхронизировано название метода с роутером
        result = await self.db.execute(
            select(Employee).offset(skip).limit(limit).order_by(Employee.id)
        )
        return result.scalars().all()