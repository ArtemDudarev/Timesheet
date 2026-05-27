import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.models.project import ProjectStatus


class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    status: ProjectStatus
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)
