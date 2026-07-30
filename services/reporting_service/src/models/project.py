import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Project(Base):
    """Реплика проекта (project.created/updated, payload расширен в A.3)."""

    __tablename__ = "project"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    budget_hours: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
