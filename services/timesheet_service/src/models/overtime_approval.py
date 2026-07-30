import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ApprovalStatus(str, enum.Enum):
    PENDING = "На согласовании"
    APPROVED = "Согласовано"
    REJECTED = "Отклонено"


class OvertimeApproval(Base):
    __tablename__ = "overtime_approval"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    time_entry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("time_entry.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    approver_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status"),
        nullable=False,
        default=ApprovalStatus.PENDING,
    )
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    time_entry: Mapped["TimeEntry"] = relationship(
        "TimeEntry", back_populates="overtime_approval", lazy="selectin"
    )
