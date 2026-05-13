from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class EmployeeRole(Base):
    __tablename__ = "employee_role"

    employee_role_id: Mapped[int] = mapped_column(primary_key=True)

    employee_role_employee_id: Mapped[int] = mapped_column(
        ForeignKey("employee.employee_id", ondelete="CASCADE"),
        nullable=False,
    )

    employee_role_role_id: Mapped[int] = mapped_column(
        ForeignKey("role.role_id", ondelete="CASCADE"),
        nullable=False,
    )

    employee: Mapped["Employee"] = relationship(
        back_populates="employee_roles"
    )

    role: Mapped["Role"] = relationship(
        back_populates="employee_roles"
    )
