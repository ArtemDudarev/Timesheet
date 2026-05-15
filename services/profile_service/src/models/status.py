import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid
from .base import Base


class Status(Base):
    __tablename__ = "status"

    status_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    status_name: Mapped[str] = mapped_column(unique=True, nullable=False)
    status_description: Mapped[str | None] = mapped_column(nullable=True)