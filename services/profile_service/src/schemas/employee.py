import uuid
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .project import ProjectRead
from .project_role import ProjectRoleResponse
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


class EmployeeCreate(EmployeeBase):
    password: str
    role_ids: List[uuid.UUID]


class EmployeeRead(EmployeeBase):
    id: uuid.UUID
    register_date: date
    image_url: Optional[str] = None
    roles: List[RoleRead]
    status: StatusRead
    projects: List[ProjectRead] = Field(default_factory=list)
    project_roles: List[ProjectRoleResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    birthday: Optional[date] = None
    image_url: Optional[str] = None


class EmployeeListRead(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: EmailStr
    number: Optional[str] = None
    status_id: uuid.UUID
    roles: List[RoleRead]

    model_config = ConfigDict(from_attributes=True)
