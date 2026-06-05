from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy import Boolean, Date, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.user_role import user_role


class User(Base):
    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    number: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    register_date: Mapped[date] = mapped_column(Date, nullable=False)

    employee: Mapped[Optional["Employee"]] = relationship(
        "Employee",
        back_populates="user",
        lazy="selectin",
        uselist=False,
    )
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=user_role,
        back_populates="users",
        lazy="selectin",
    )
