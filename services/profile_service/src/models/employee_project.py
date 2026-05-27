import enum
import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Date, Enum, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AssignmentStatus(str, enum.Enum):
    REQUEST = "Заявка"
    ACTIVE = "Привлечён"
    EXTENDED = "Продлён"
    REMOVED = "Снят с проекта"


class EmployeeProject(Base):
    __tablename__ = "employee_project"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("employee.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    project_role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_role.id", ondelete="RESTRICT"), nullable=False
    )
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, name="assignment_status"),
        nullable=False,
        default=AssignmentStatus.REQUEST,
    )

    employee: Mapped["Employee"] = relationship("Employee", back_populates="assignments")
    project: Mapped["Project"] = relationship("Project", lazy="selectin")
    project_role: Mapped["ProjectRole"] = relationship("ProjectRole", lazy="selectin")
