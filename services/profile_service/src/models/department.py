import uuid
from typing import Optional

from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Department(Base):
    __tablename__ = "department"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
