from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.employee import Employee
from src.schemas.employee import EmployeeCreate, EmployeeUpdate
from typing import List, Optional


class EmployeeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_employee(self, employee_in: EmployeeCreate) -> Employee:
        employee = Employee(
            employee_first_name=employee_in.employee_first_name,
            employee_last_name=employee_in.employee_last_name,
            employee_email=employee_in.employee_email,
            employee_password=employee_in.employee_password,  # должен быть захеширован!
            employee_number=employee_in.employee_number,
            employee_phone=employee_in.employee_phone,
            employee_address=employee_in.employee_address,
            employee_birthday=employee_in.employee_birthday,
            employee_role_id=employee_in.employee_role_id,
            employee_status_id=employee_in.employee_status_id,
            employee_register_date=date.today()
        )
        self.db.add(employee)
        await self.db.commit()
        await self.db.refresh(employee)
        return employee

    async def get_employee_by_id(self, employee_id: int) -> Optional[Employee]:
        result = await self.db.execute(
            select(Employee).where(Employee.employee_id == employee_id)
        )
        return result.scalar_one_or_none()

    async def get_employee_by_email(self, email: str) -> Optional[Employee]:
        result = await self.db.execute(
            select(Employee).where(Employee.employee_email == email)
        )
        return result.scalar_one_or_none()

    async def get_employees(self, skip: int = 0, limit: int = 100) -> List[Employee]:
        result = await self.db.execute(
            select(Employee).offset(skip).limit(limit).order_by(Employee.employee_id)
        )
        return result.scalars().all()