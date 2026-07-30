import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ApprovalRefType(str, enum.Enum):
    # Карточка согласования только ССЫЛАЕТСЯ на реальную запись в
    # timesheet_service/absence_service — собственного статуса не хранит
    # (требование контракта из критического ревью)
    OVERTIME = "OVERTIME"
    ABSENCE = "ABSENCE"


class Message(Base):
    __tablename__ = "message"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    channel_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("channel.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reply_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("message.id", ondelete="SET NULL"), nullable=True
    )
    forwarded_from_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("message.id", ondelete="SET NULL"), nullable=True
    )
    edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    related_approval_type: Mapped[Optional[ApprovalRefType]] = mapped_column(
        Enum(ApprovalRefType, name="approval_ref_type"), nullable=True
    )
    related_approval_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
