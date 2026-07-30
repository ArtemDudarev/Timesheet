import uuid

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Department(Base):
    """Реплика справочника отделов (источник — management_service, department.*)."""

    __tablename__ = "department"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
