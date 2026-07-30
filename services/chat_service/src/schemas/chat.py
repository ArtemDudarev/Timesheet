import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator

from src.models.channel import ChannelType
from src.models.message import ApprovalRefType


class EmployeeShort(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str

    model_config = ConfigDict(from_attributes=True)


class ChannelRead(BaseModel):
    id: uuid.UUID
    type: ChannelType
    name: Optional[str]
    project_id: Optional[uuid.UUID]
    pinned: bool = False
    muted: bool = False
    companion: Optional[EmployeeShort] = None  # для DM — собеседник


class MessageCreate(BaseModel):
    text: Optional[str] = None
    reply_to_id: Optional[uuid.UUID] = None
    related_approval_type: Optional[ApprovalRefType] = None
    related_approval_id: Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def text_or_approval(self) -> "MessageCreate":
        if not self.text and not self.related_approval_id:
            raise ValueError("Сообщение должно содержать text или ссылку на согласование")
        if (self.related_approval_type is None) != (self.related_approval_id is None):
            raise ValueError("related_approval_type и related_approval_id задаются вместе")
        return self


class MessageUpdate(BaseModel):
    text: str


class MessageRead(BaseModel):
    id: uuid.UUID
    channel_id: uuid.UUID
    author_id: uuid.UUID
    text: Optional[str]
    reply_to_id: Optional[uuid.UUID]
    forwarded_from_id: Optional[uuid.UUID]
    edited: bool
    related_approval_type: Optional[ApprovalRefType]
    related_approval_id: Optional[uuid.UUID]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
