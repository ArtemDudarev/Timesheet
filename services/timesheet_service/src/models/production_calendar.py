import enum
from datetime import date
from typing import Optional

from sqlalchemy import Date, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DayType(str, enum.Enum):
    WORKING = "Рабочий"
    WEEKEND = "Выходной"
    HOLIDAY = "Праздник"
    PRE_HOLIDAY = "Предпраздничный"


class ProductionCalendar(Base):
    __tablename__ = "production_calendar"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    day_type: Mapped[DayType] = mapped_column(
        Enum(DayType, name="day_type"), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
