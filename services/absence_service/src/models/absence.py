import enum
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AbsenceStatus(str, enum.Enum):
    DRAFT = "Черновик"
    PENDING = "На согласовании"
    APPROVED = "Согласована"
    REJECTED = "Отклонена"
    CANCELLED = "Отменена"


class Absence(Base):
    __tablename__ = "absence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("absence_type.id"), nullable=False
    )
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    # Рабочие дни пн-пт; праздники не учитываются — производственный календарь
    # живёт в timesheet_service (см. открытый вопрос №9 контракта)
    days_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AbsenceStatus] = mapped_column(
        Enum(AbsenceStatus, name="absence_status"),
        nullable=False,
        default=AbsenceStatus.DRAFT,
    )
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approver_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    absence_type: Mapped["AbsenceType"] = relationship("AbsenceType", lazy="selectin")
