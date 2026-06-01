import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.schemas.project_status import ProjectStatusResponse


class ProjectCreate(BaseModel):
    name: str
    status_id: uuid.UUID
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    status_id: uuid.UUID
    project_status: ProjectStatusResponse
    start_date: Optional[date]
    end_date: Optional[date]

    model_config = ConfigDict(from_attributes=True)


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    status_id: Optional[uuid.UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
