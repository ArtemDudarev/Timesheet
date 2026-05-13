import uuid
from typing import List
from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
# from .employee_project import employee_project

class Project(Base):
    __tablename__ = "project"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4
    )

    project_name: Mapped[str] = mapped_column(
        String(255),
        name="project_name",
        unique=True,
        nullable=False
    )

    project_status: Mapped[str] = mapped_column(
        String(100),
        name="project_status",
        nullable=False
    )

    employees: Mapped[List["Employee"]] = relationship(
        "Employee",
        secondary=employee_project,
        back_populates="project",
        lazy="selectin"
    )