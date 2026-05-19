from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy import Date, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.employee_project import employee_project
from src.models.employee_project_role import employee_project_role_table
from src.models.employee_role import employee_role


class Employee(Base):
    __tablename__ = "employee"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    number: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    birthday: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    register_date: Mapped[date] = mapped_column(Date, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    status_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("status.id"),
        nullable=False,
    )

    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=employee_role,
        back_populates="employees",
        lazy="selectin",
    )

    status: Mapped["Status"] = relationship(
        "Status",
        back_populates="employees",
        lazy="selectin",
    )

    projects: Mapped[List["Project"]] = relationship(
        "Project",
        secondary=employee_project,
        back_populates="employees",
        lazy="selectin",
    )

    project_roles: Mapped[List["ProjectRole"]] = relationship(
        "ProjectRole",
        secondary=employee_project_role_table,
        back_populates="employees",
        lazy="selectin",
    )
