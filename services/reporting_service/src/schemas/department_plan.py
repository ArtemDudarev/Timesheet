import uuid
from typing import Optional

from pydantic import BaseModel, Field


class DepartmentPlanCreate(BaseModel):
    department_id: uuid.UUID
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    planned_hours: float = Field(gt=0)


class DepartmentPlanUpdate(BaseModel):
    planned_hours: Optional[float] = Field(default=None, gt=0)


class DepartmentPlanRead(BaseModel):
    id: uuid.UUID
    department_id: uuid.UUID
    year: int
    month: int
    planned_hours: float

    model_config = {"from_attributes": True}
