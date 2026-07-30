import uuid
from datetime import date

from sqlalchemy import Date, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Absence(Base):
    """Тонкая реплика отсутствия (absence.status_changed из absence_service).

    Нужна для блокировки записей табеля на даты согласованных отсутствий.
    """

    __tablename__ = "absence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    type_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
