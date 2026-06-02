import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator

from src.schemas.assignment_status import AssignmentStatusResponse
from src.schemas.project import ProjectRead
from src.schemas.project_role import ProjectRoleResponse


class AssignmentRead(BaseModel):
    id: uuid.UUID
    project: ProjectRead
    project_role: ProjectRoleResponse
    assignment_status: AssignmentStatusResponse
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class AssignmentCreate(BaseModel):
    project_id: uuid.UUID
    project_role_id: uuid.UUID
    assignment_status_id: uuid.UUID
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "AssignmentCreate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date не может быть раньше start_date")
        return self


class AssignmentUpdate(BaseModel):
    project_role_id: Optional[uuid.UUID] = None
    assignment_status_id: Optional[uuid.UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "AssignmentUpdate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date не может быть раньше start_date")
        return self
