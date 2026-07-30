import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TimeEntryReplica(Base):
    """Реплика записи табеля (timesheet.entry_created/updated/deleted).

    Упсерт по entry_id — идемпотентен при повторной доставке/реплее,
    поэтому агрегаты считаются на чтении, а не инкрементально.
    """

    __tablename__ = "time_entry_replica"

    entry_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    period_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True, index=True)
    type_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    spend_time: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    month: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
