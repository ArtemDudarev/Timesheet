from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class Status(Base):
    __tablename__ = "statuses"

    status_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status_name: Mapped[str] = mapped_column(unique=True, nullable=False)
    status_description: Mapped[str | None] = mapped_column(nullable=True)