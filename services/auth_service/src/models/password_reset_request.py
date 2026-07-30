from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ResetRequestStatus(str, enum.Enum):
    PENDING = "Ожидает"
    RESOLVED = "Обработана"
    CANCELLED = "Отменена"


class PasswordResetRequest(Base):
    __tablename__ = "password_reset_request"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    identifier: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Без FK: пользователь может быть не найден по identifier — заявка всё равно сохраняется,
    # чтобы снаружи нельзя было понять, существует ли аккаунт
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    status: Mapped[ResetRequestStatus] = mapped_column(
        Enum(ResetRequestStatus, name="reset_request_status"),
        nullable=False,
        default=ResetRequestStatus.PENDING,
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
