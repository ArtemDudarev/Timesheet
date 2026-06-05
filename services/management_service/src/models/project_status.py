import uuid
from typing import Optional

from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ProjectStatus(Base):
    __tablename__ = "project_status"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
