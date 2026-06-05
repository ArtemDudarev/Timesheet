import uuid
from datetime import datetime

from pydantic import BaseModel


class SessionRead(BaseModel):
    id: uuid.UUID
    device: str
    ip_address: str | None
    created_at: datetime
    is_current: bool
