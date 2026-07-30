import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class PeriodStatus(str, enum.Enum):
    OPEN = "Открыт"
    CLOSED = "Закрыт"


class SubmissionStatus(str, enum.Enum):
    DRAFT = "Черновик"
    PENDING = "На согласовании"
    APPROVED = "Согласован"
    REJECTED = "Отклонён"


class TimesheetPeriod(Base):
    __tablename__ = "timesheet_period"
    __table_args__ = (
        UniqueConstraint("employee_id", "year", "month", name="uq_period_employee_year_month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("employee.id", ondelete="CASCADE"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PeriodStatus] = mapped_column(
        Enum(PeriodStatus, name="period_status"),
        nullable=False,
        default=PeriodStatus.OPEN,
    )
    closed_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    submission_status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status"),
        nullable=False,
        default=SubmissionStatus.DRAFT,
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", lazy="selectin")
    entries: Mapped[list["TimeEntry"]] = relationship(
        "TimeEntry", back_populates="period", lazy="selectin"
    )
