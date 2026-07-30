import uuid
from typing import Optional

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Employee(Base):
    """Тонкая реплика (employee.profile_created / employee.updated)."""

    __tablename__ = "employee"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
