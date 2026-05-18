import uuid
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr

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


class EmployeeRead(EmployeeBase):
    id: uuid.UUID
    register_date: date
    image_url: Optional[str] = None
    roles: List[RoleRead]

    model_config = ConfigDict(from_attributes=True)


class EmployeeListRead(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    number: Optional[str] = None
    status_id: uuid.UUID
    roles: List[RoleRead]

    model_config = ConfigDict(from_attributes=True)
