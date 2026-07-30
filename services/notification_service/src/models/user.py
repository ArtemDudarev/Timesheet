import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    register_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary="user_role", lazy="selectin"
    )
