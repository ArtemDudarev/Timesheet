import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from src.models.overtime_approval import ApprovalStatus
from src.schemas.time_entry import AssignmentShort


class OvertimeApprovalResolve(BaseModel):
    comment: Optional[str] = None


class OvertimeEntryShort(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    date_from: date
    date_to: date
    spend_time: float
    task_name: Optional[str]
    assignment: Optional[AssignmentShort]

    model_config = {"from_attributes": True}


class OvertimeApprovalResponse(BaseModel):
    id: uuid.UUID
    time_entry_id: uuid.UUID
    approver_id: Optional[uuid.UUID]
    status: ApprovalStatus
    comment: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]
    time_entry: Optional[OvertimeEntryShort] = None

    model_config = {"from_attributes": True}
