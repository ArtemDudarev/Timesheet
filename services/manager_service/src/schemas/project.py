import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from src.models.project import ProjectStatus


class ProjectBase(BaseModel):
    name: str
    status: ProjectStatus = ProjectStatus.PLANNED
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = [s.value for s in ProjectStatus]
        if v not in valid:
            raise ValueError(
                f"Недопустимый статус '{v}'. "
                f"Допустимые значения: {', '.join(valid)}"
            )
        return v


class ProjectCreate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[ProjectStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v is None:
            return v
        valid = [s.value for s in ProjectStatus]
        if v not in valid:
            raise ValueError(
                f"Недопустимый статус '{v}'. "
                f"Допустимые значения: {', '.join(valid)}"
            )
        return v
