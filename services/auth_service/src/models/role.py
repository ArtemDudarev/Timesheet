from typing import List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text
from .employee_role import employee_role
from .base import Base

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    employees: Mapped[List["Employee"]] = relationship(
        "Employee",
        secondary=employee_role,
        back_populates="roles"
    ) 