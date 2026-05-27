import uuid
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .assignment import AssignmentRead
from .role import RoleRead
from .status import StatusRead


class UserRead(BaseModel):
    email: EmailStr
    number: Optional[str] = None
    is_active: bool
    register_date: date
    roles: List[RoleRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class EmployeeRead(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    birthday: Optional[date] = None
    image_url: Optional[str] = None
    status: StatusRead
    assignments: List[AssignmentRead] = Field(default_factory=list)
    user: UserRead

    model_config = ConfigDict(from_attributes=True)


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    birthday: Optional[date] = None
    image_url: Optional[str] = None
