import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from src.models.overtime_approval import ApprovalStatus


class OvertimeApprovalResolve(BaseModel):
    comment: Optional[str] = None


class OvertimeApprovalResponse(BaseModel):
    id: uuid.UUID
    time_entry_id: uuid.UUID
    approver_id: Optional[uuid.UUID]
    status: ApprovalStatus
    comment: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]

    model_config = {"from_attributes": True}
