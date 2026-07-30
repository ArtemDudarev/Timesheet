import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ChannelType(str, enum.Enum):
    # Английские коды-дискриминаторы (как NotificationType)
    GROUP = "GROUP"
    DM = "DM"


class Channel(Base):
    __tablename__ = "channel"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    type: Mapped[ChannelType] = mapped_column(
        Enum(ChannelType, name="channel_type"), nullable=False
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, nullable=True, unique=True
    )

    members: Mapped[list["ChannelMember"]] = relationship(
        "ChannelMember",
        back_populates="channel",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class ChannelMember(Base):
    __tablename__ = "channel_member"

    channel_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("channel.id", ondelete="CASCADE"), primary_key=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    muted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    channel: Mapped["Channel"] = relationship(
        "Channel", back_populates="members", lazy="selectin"
    )
