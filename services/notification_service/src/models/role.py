import uuid
from typing import Optional

from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Role(Base):
    __tablename__ = "role"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
