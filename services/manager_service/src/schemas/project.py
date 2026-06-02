import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator

from src.schemas.project_status import ProjectStatusResponse


class ProjectCreate(BaseModel):
    name: str
    project_status_id: uuid.UUID
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "ProjectCreate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date не может быть раньше start_date")
        return self


class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    project_status: ProjectStatusResponse
    start_date: Optional[date]
    end_date: Optional[date]

    model_config = ConfigDict(from_attributes=True)


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    project_status_id: Optional[uuid.UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "ProjectUpdate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date не может быть раньше start_date")
        return self
