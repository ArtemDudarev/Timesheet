from __future__ import annotations

import uuid

from sqlalchemy import String, Text
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Role(Base):
    __tablename__ = "role"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    employee_roles: Mapped[list["EmployeeRole"]] = relationship(
        back_populates="role"
    )
