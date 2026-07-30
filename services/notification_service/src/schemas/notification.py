import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from src.models.notification import NotificationType


class NotificationRead(BaseModel):
    id: uuid.UUID
    type: NotificationType
    title: str
    text: str
    target_url: Optional[str]
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationPreferenceRead(BaseModel):
    email_enabled: bool
    push_enabled: bool
    type_toggles: dict[str, bool]

    model_config = {"from_attributes": True}


class NotificationPreferenceUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    type_toggles: Optional[dict[str, bool]] = None
