import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, model_validator

from src.schemas.entry_type_ref import EntryTypeRefResponse


class ProjectShort(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class ProjectRoleShort(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class AssignmentShort(BaseModel):
    id: uuid.UUID
    project: ProjectShort
    project_role: ProjectRoleShort

    model_config = {"from_attributes": True}


class OvertimeApprovalShort(BaseModel):
    id: uuid.UUID
    status: str

    model_config = {"from_attributes": True}


class TimeEntryCreate(BaseModel):
    type_id: uuid.UUID
    assignment_id: Optional[uuid.UUID] = None
    date_from: date
    date_to: date
    spend_time: Optional[float] = None
    task_name: Optional[str] = None
    task_num: Optional[str] = None
    comment: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.date_to < self.date_from:
            raise ValueError("date_to не может быть раньше date_from")
        return self


class TimeEntryUpdate(BaseModel):
    spend_time: Optional[float] = None
    task_name: Optional[str] = None
    task_num: Optional[str] = None
    comment: Optional[str] = None


class TimeEntryResponse(BaseModel):
    id: uuid.UUID
    timesheet_period_id: uuid.UUID
    entry_type: EntryTypeRefResponse
    assignment: Optional[AssignmentShort]
    date_from: date
    date_to: date
    spend_time: float
    task_name: Optional[str]
    task_num: Optional[str]
    comment: Optional[str]
    created_at: datetime
    updated_at: datetime
    overtime_approval: Optional[OvertimeApprovalShort]

    model_config = {"from_attributes": True}
