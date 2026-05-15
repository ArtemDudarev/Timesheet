import uuid
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List
from .role import RoleRead

class EmployeeBase(BaseModel):
    email: EmailStr
    employee_number: str

class EmployeeCreate(EmployeeBase):
    password: str
    role_id: List[uuid.UUID]  # ИСПРАВЛЕНО: было List[int]

class EmployeeRead(EmployeeBase):
    id: uuid.UUID
    roles: List[RoleRead]

    model_config = ConfigDict(from_attributes=True)

class EmployeeLogin(BaseModel):
    email: EmailStr | None = None
    employee_number: str | None = None
    password: str
    
class EmployeeCreateSimple(BaseModel):
    email: EmailStr
    password: str