import uuid
from datetime import datetime

from pydantic import BaseModel

from src.models.timesheet_period import PeriodStatus, SubmissionStatus


class EmployeeShort(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str

    model_config = {"from_attributes": True}


class TimesheetPeriodResponse(BaseModel):
    id: uuid.UUID
    employee: EmployeeShort
    year: int
    month: int
    status: PeriodStatus
    closed_by: uuid.UUID | None
    closed_at: datetime | None
    submission_status: SubmissionStatus
    submitted_at: datetime | None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    rejection_comment: str | None

    model_config = {"from_attributes": True}


class TimesheetPeriodClose(BaseModel):
    pass


class TimesheetPeriodReject(BaseModel):
    comment: str
