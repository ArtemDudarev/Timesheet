import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.models.employee_project import AssignmentStatus
from .project import ProjectRead
from .project_role import ProjectRoleResponse


class AssignmentRead(BaseModel):
    id: uuid.UUID
    project: ProjectRead
    project_role: ProjectRoleResponse
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: AssignmentStatus

    model_config = ConfigDict(from_attributes=True)
