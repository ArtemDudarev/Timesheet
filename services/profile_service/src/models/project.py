import enum
import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Date, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ProjectStatus(str, enum.Enum):
    PLANNED   = "Планируется"
    ACTIVE    = "Активный"
    ON_HOLD   = "Приостановлен"
    COMPLETED = "Завершён"
    ARCHIVED  = "Архивный"


class Project(Base):
    __tablename__ = "project"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status"),
        nullable=False,
        default=ProjectStatus.PLANNED,
    )
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
