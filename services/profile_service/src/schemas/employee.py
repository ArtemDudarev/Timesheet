import uuid
from datetime import date
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from .role import RoleRead

class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    number: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    birthday: Optional[date] = None
    status_id: uuid.UUID

class EmployeeCreate(EmployeeBase):
    password: str
    role_ids: List[uuid.UUID]  # ИСПРАВЛЕНО: Список UUID вместо int

class EmployeeRead(EmployeeBase):
    id: uuid.UUID
    register_date: date
    image_url: Optional[str] = None
    roles: List[RoleRead]

    model_config = ConfigDict(from_attributes=True)

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    birthday: Optional[date] = None
    image_url: Optional[str] = None
    status_id: Optional[uuid.UUID] = None
    role_ids: Optional[List[uuid.UUID]] = None

class EmployeeListRead(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    number: Optional[str] = None
    status_id: uuid.UUID
    roles: List[RoleRead]

    model_config = ConfigDict(from_attributes=True)