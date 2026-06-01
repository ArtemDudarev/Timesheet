import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.schemas.assignment_status import AssignmentStatusResponse
from src.schemas.project import ProjectRead
from src.schemas.project_role import ProjectRoleResponse


class AssignmentRead(BaseModel):
    id: uuid.UUID
    project: ProjectRead
    project_role: ProjectRoleResponse
    status_id: uuid.UUID
    assignment_status: AssignmentStatusResponse
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class AssignmentCreate(BaseModel):
    project_id: uuid.UUID
    project_role_id: uuid.UUID
    status_id: uuid.UUID
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class AssignmentUpdate(BaseModel):
    project_role_id: Optional[uuid.UUID] = None
    status_id: Optional[uuid.UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
