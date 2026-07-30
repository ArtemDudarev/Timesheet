import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.models.password_reset_request import ResetRequestStatus


class PasswordResetRequestCreate(BaseModel):
    identifier: str  # email или номер сотрудника


class PasswordResetRequestRead(BaseModel):
    id: uuid.UUID
    identifier: str
    status: ResetRequestStatus
    requested_at: datetime
    resolved_by: Optional[uuid.UUID]
    resolved_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
