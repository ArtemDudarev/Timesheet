import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Project(Base):
    __tablename__ = "project"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("project_status.id"), nullable=False
    )
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    client: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    project_status: Mapped["ProjectStatus"] = relationship("ProjectStatus", lazy="selectin")
