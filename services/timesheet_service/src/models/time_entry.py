import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class TimeEntry(Base):
    __tablename__ = "time_entry"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    timesheet_period_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("timesheet_period.id", ondelete="CASCADE"), nullable=False
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("employee.id", ondelete="CASCADE"), nullable=False
    )
    assignment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("assignment.id", ondelete="SET NULL"), nullable=True
    )
    type_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("entry_type_ref.id"), nullable=False
    )
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    spend_time: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    task_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    task_num: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    period: Mapped["TimesheetPeriod"] = relationship(
        "TimesheetPeriod", back_populates="entries"
    )
    entry_type: Mapped["EntryTypeRef"] = relationship(
        "EntryTypeRef", lazy="selectin"
    )
    assignment: Mapped[Optional["Assignment"]] = relationship(
        "Assignment", lazy="selectin"
    )
    overtime_approval: Mapped[Optional["OvertimeApproval"]] = relationship(
        "OvertimeApproval", back_populates="time_entry", uselist=False, lazy="selectin",
        cascade="all, delete-orphan", passive_deletes=True,
    )
