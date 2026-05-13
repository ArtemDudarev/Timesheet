from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Role(Base):
    __tablename__ = "role"

    role_id: Mapped[int] = mapped_column(primary_key=True)
    role_name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    role_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    employee_roles: Mapped[list["EmployeeRole"]] = relationship(
        back_populates="role"
    )
