import uuid
from typing import Optional

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Project(Base):
    __tablename__ = "project"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Машинный код статуса (ACTIVE/PLANNED/...) — `status` хранит человекочитаемое название
    status_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
