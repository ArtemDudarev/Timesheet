import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class NotificationType(str, enum.Enum):
    # Английские коды-дискриминаторы: должны совпадать с ключами
    # NotificationPreference.type_toggles (как ProjectStatus.code в management_service)
    APPROVAL = "APPROVAL"
    DOC = "DOC"
    CHAT = "CHAT"
    DEADLINE = "DEADLINE"
    MENTION = "MENTION"
    PASSWORD = "PASSWORD"


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    target_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
