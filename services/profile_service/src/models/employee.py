from typing import Optional
import uuid
from datetime import date
from sqlalchemy import Column, Integer, String, ForeignKey, Date, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as Uuid
from src.core.database import Base


class Employee(Base):
    __tablename__ = "employee"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    
    employee_first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    employee_last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    employee_email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    employee_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    employee_number: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    employee_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    employee_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    employee_birthday: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    employee_register_date: Mapped[date] = mapped_column(Date, nullable=False)
    employee_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Foreign Key
    employee_status_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("status.status_id"), nullable=False
    )

    # === Many-to-Many с ролями ===
    roles: Mapped[list["EmployeeRole"]] = relationship(
        "EmployeeRole",
        secondary="employee_employee_role",   # название ассоциативной таблицы
        back_populates="employees",
        lazy="selectin"                       # удобно для API
    )

    # Relationships
    status: Mapped["Status"] = relationship("Status", back_populates="employees")
    
    projects: Mapped[list["EmployeeProject"]] = relationship(
        "EmployeeProject", back_populates="employee"
    )
    project_roles: Mapped[list["EmployeeProjectRole"]] = relationship(
        "EmployeeProjectRole", back_populates="employee"
    )