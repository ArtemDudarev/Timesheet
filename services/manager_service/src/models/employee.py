from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy import Date, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Employee(Base):
    __tablename__ = "employee"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    birthday: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    status_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("status.id"), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="employee", lazy="selectin")
    status: Mapped["Status"] = relationship("Status", back_populates="employees", lazy="selectin")
    assignments: Mapped[List["EmployeeProject"]] = relationship(
        "EmployeeProject",
        back_populates="employee",
        lazy="selectin",
    )
