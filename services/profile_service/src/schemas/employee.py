import uuid
from datetime import date
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from .role import RoleRead  # Импортируем схему роли


class EmployeeBase(BaseModel):
    employee_first_name: str
    employee_last_name: str
    employee_email: EmailStr
    employee_number: Optional[str] = None
    employee_phone: Optional[str] = None
    employee_address: Optional[str] = None
    employee_birthday: Optional[date] = None
    employee_status_id: int


class EmployeeCreate(EmployeeBase):
    employee_password: str
    # Теперь список ролей (можно передавать несколько role_id)
    role_ids: List[int]


class EmployeeRead(EmployeeBase):
    employee_id: uuid.UUID
    employee_register_date: date
    employee_image_url: Optional[str] = None
    
    # Возвращаем полные объекты ролей
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
    employee_status_id: Optional[int] = None
    # При обновлении тоже можно менять роли
    role_ids: Optional[List[int]] = None


# Дополнительная схема (удобно для списка сотрудников)
class EmployeeListRead(BaseModel):
    employee_id: uuid.UUID
    employee_first_name: str
    employee_last_name: str
    employee_email: EmailStr
    employee_number: Optional[str] = None
    roles: List[RoleRead]
    employee_status_id: int

    model_config = {
        "from_attributes": True
    }