import uuid
from typing import Optional

from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DocumentType(Base):
    __tablename__ = "document_type"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
