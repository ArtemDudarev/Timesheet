import uuid
from datetime import datetime

from pydantic import BaseModel

from src.models.timesheet_period import PeriodStatus


class EmployeeShort(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str

    model_config = {"from_attributes": True}


class TimesheetPeriodResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    employee: EmployeeShort
    year: int
    month: int
    status: PeriodStatus
    closed_by: uuid.UUID | None
    closed_at: datetime | None

    model_config = {"from_attributes": True}


class TimesheetPeriodClose(BaseModel):
    pass
