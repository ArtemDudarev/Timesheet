import uuid
from pydantic import BaseModel, EmailStr
from typing import List
from .role import RoleRead # Импортируем схему роли для EmployeeRead

class EmployeeBase(BaseModel):
    email: EmailStr
    employee_number: str

class EmployeeCreate(EmployeeBase):
    password: str
    # Изменяем на список ID ролей
    role_id: List[int] 

class EmployeeRead(EmployeeBase):
    id: uuid.UUID
    # Возвращаем список полных объектов ролей
    roles: List[RoleRead]

    class Config:
        from_attributes = True

class EmployeeLogin(BaseModel):
    email: EmailStr | None = None
    employee_number: str | None = None
    password: str