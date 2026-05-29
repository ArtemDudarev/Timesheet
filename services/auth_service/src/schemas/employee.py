import re
import uuid
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from .role import RoleRead


def _validate_password(v: str) -> str:
    errors = []
    if len(v) < 8:
        errors.append("минимум 8 символов")
    if not re.search(r"[A-Z]", v):
        errors.append("минимум одна заглавная буква")
    if not re.search(r"[a-z]", v):
        errors.append("минимум одна строчная буква")
    if not re.search(r"\d", v):
        errors.append("минимум одна цифра")
    if not re.search(r"[!@#$%^&*()\-_=+\[\]{};:'\",.<>?/\\|`~]", v):
        errors.append("минимум один специальный символ")
    if errors:
        raise ValueError(", ".join(errors))
    return v


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    number: str
    is_active: bool
    register_date: date
    roles: List[RoleRead]

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role_ids: List[uuid.UUID] = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password(v)


class UserLogin(BaseModel):
    email: Optional[EmailStr] = None
    number: Optional[str] = None
    password: str

    @model_validator(mode="after")
    def require_email_or_number(self) -> "UserLogin":
        if not self.email and not self.number:
            raise ValueError("Необходимо указать email или номер сотрудника")
        return self


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return _validate_password(v)

    @model_validator(mode="after")
    def passwords_differ(self) -> "PasswordChange":
        if self.current_password == self.new_password:
            raise ValueError("Новый пароль должен отличаться от текущего")
        return self


class PasswordResetResponse(BaseModel):
    temp_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool = False
