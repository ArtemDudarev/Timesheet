import uuid

from sqlalchemy import JSON, Boolean, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

DEFAULT_TYPE_TOGGLES: dict[str, bool] = {
    "APPROVAL": True,
    "DOC": True,
    "CHAT": True,
    "DEADLINE": True,
    "MENTION": True,
    "WEEKLY_DIGEST": False,
}


class NotificationPreference(Base):
    __tablename__ = "notification_preference"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    push_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    type_toggles: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: dict(DEFAULT_TYPE_TOGGLES)
    )
