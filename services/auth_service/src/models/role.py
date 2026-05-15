import uuid
from typing import List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Uuid
from .employee_role import employee_role
from .base import Base

class Role(Base):
    __tablename__ = "role"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)

    employees: Mapped[List["Employee"]] = relationship(
        "Employee",
        secondary=employee_role,
        back_populates="roles"
    )