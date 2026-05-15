import uuid
from datetime import date
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from .role import RoleRead


class EmployeeBase(BaseModel):
    employee_first_name: str
    employee_last_name: str
    employee_email: EmailStr
    employee_number: Optional[str] = None
    employee_phone: Optional[str] = None
    employee_address: Optional[str] = None
    employee_birthday: Optional[date] = None
    employee_status_id: uuid.UUID          # ← исправлено на UUID


class EmployeeCreate(EmployeeBase):
    employee_password: str
    role_ids: List[int]                    # список id ролей


class EmployeeRead(EmployeeBase):
    employee_id: uuid.UUID
    employee_register_date: date
    employee_image_url: Optional[str] = None
    roles: List[RoleRead]

    model_config = {
        "from_attributes": True
    }


class EmployeeUpdate(BaseModel):
    employee_first_name: Optional[str] = None
    employee_last_name: Optional[str] = None
    employee_phone: Optional[str] = None
    employee_address: Optional[str] = None
    employee_birthday: Optional[date] = None
    employee_image_url: Optional[str] = None
    employee_status_id: Optional[uuid.UUID] = None   # ← исправлено
    role_ids: Optional[List[int]] = None


# Для получения списка сотрудников
class EmployeeListRead(BaseModel):
    employee_id: uuid.UUID
    employee_first_name: str
    employee_last_name: str
    employee_email: EmailStr
    employee_number: Optional[str] = None
    employee_status_id: uuid.UUID                    # ← исправлено
    roles: List[RoleRead]

    model_config = {
        "from_attributes": True
    }