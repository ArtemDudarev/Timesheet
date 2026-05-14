import uuid
from typing import List 
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Uuid

from src.models.base import Base
from .employee_role import employee_role

class Employee(Base):
    __tablename__ = "employee"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    
    email: Mapped[str] = mapped_column(
        String(255), name="employee_email", unique=True, index=True, nullable=False
    )
    
    hashed_password: Mapped[str] = mapped_column(
        String(255), name="employee_password", nullable=False
    )
    
    employee_number: Mapped[str] = mapped_column(
        String(50), name="employee_number", unique=True, nullable=False
    )

    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=employee_role,
        back_populates="employees",
        lazy="selectin"  # <--- Добавьте это!
    )