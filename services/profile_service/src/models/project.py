import uuid
from typing import List
from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .employee_project import employee_project

class Project(Base):
    __tablename__ = "project"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(100), nullable=False)

    employees: Mapped[List["Employee"]] = relationship(
        "Employee",
        secondary=employee_project,
        back_populates="projects",
        lazy="selectin"
    )