import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from src.models.employee_project import AssignmentStatus
from .project import ProjectRead
from .project_role import ProjectRoleResponse


def _validate_assignment_status(v: str) -> str:
    valid = [s.value for s in AssignmentStatus]
    if v not in valid:
        raise ValueError(
            f"Недопустимый статус назначения '{v}'. "
            f"Допустимые значения: {', '.join(valid)}"
        )
    return v


class AssignmentRead(BaseModel):
    id: uuid.UUID
    project: ProjectRead
    project_role: ProjectRoleResponse
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: AssignmentStatus

    model_config = ConfigDict(from_attributes=True)


class AssignmentCreate(BaseModel):
    project_id: uuid.UUID
    project_role_id: uuid.UUID
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: AssignmentStatus = AssignmentStatus.REQUEST

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: str) -> str:
        return _validate_assignment_status(v)


class AssignmentUpdate(BaseModel):
    project_role_id: Optional[uuid.UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[AssignmentStatus] = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v is None:
            return v
        return _validate_assignment_status(v)
