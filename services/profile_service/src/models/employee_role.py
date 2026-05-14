from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class EmployeeRole(Base):
    __tablename__ = "employee_role"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("employee.id", ondelete="CASCADE"),
        nullable=False,
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("role.id", ondelete="CASCADE"),
        nullable=False,
    )

    employee: Mapped["Employee"] = relationship(
        back_populates="employee_roles"
    )

    role: Mapped["Role"] = relationship(
        back_populates="employee_roles"
    )
