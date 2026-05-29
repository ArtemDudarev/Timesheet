import uuid
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from .role import RoleRead


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    number: Optional[str] = None
    is_active: bool
    register_date: date
    roles: List[RoleRead]

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    number: str
    password: str
    role_ids: List[uuid.UUID]


class UserRegister(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: Optional[EmailStr] = None
    number: Optional[str] = None
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
