from __future__ import annotations
import uuid
from datetime import date
from typing import List, Optional
from sqlalchemy import String, Text, Date, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.employee_role import employee_role
from src.models.employee_project import employee_project

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

    status_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("status.id"), nullable=False)

    # ИСПРАВЛЕНО: Связь указывает на целевой класс "Role"
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=employee_role,
        back_populates="employees",
        lazy="selectin"
    )

    status: Mapped["Status"] = relationship("Status", back_populates="employees")

    # ИСПРАВЛЕНО: Связь указывает на целевой класс "Project" через secondary-таблицу
    projects: Mapped[List["Project"]] = relationship(
        "Project", 
        secondary=employee_project,
        back_populates="employees",
        lazy="selectin"
    )

    # # Оставляем, если класс EmployeeProjectRole объявлен в другой части кода коллег
    # project_roles: Mapped[List["EmployeeProjectRole"]] = relationship(
    #     "EmployeeProjectRole", back_populates="employee"
    # )
