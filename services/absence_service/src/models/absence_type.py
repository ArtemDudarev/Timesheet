import uuid

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AbsenceType(Base):
    __tablename__ = "absence_type"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
