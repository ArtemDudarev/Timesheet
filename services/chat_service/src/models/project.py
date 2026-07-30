import uuid

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Project(Base):
    """Тонкая реплика (project.created/updated) — имена проектных каналов."""

    __tablename__ = "project"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
