import uuid
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .assignment import AssignmentRead
from .role import RoleRead
from .status import StatusRead


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
    roles: List[RoleRead] = Field(default_factory=list)
    status: StatusRead
    assignments: List[AssignmentRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class EmployeeListRead(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    number: Optional[str] = None
    status_id: uuid.UUID
    roles: List[RoleRead] = Field(default_factory=list)
    status: StatusRead
    assignments: List[AssignmentRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class EmployeeRolesUpdate(BaseModel):
    role_ids: list[uuid.UUID]


class EmployeeStatusUpdate(BaseModel):
    status_id: uuid.UUID
