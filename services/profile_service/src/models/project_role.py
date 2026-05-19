import uuid
from typing import List

from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .employee_project_role import employee_project_role_table


class ProjectRole(Base):
    __tablename__ = "project_role"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    employees: Mapped[List["Employee"]] = relationship(
        "Employee",
        secondary=employee_project_role_table,
        back_populates="project_roles",
        lazy="selectin",
    )
