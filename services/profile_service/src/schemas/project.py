import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict

from .project_status import ProjectStatusResponse


class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    project_status: ProjectStatusResponse
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)
