import uuid

from sqlalchemy import Column, ForeignKey, String, Table, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

employee_skill = Table(
    "employee_skill",
    Base.metadata,
    Column("employee_id", Uuid, ForeignKey("employee.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", Uuid, ForeignKey("skill.id", ondelete="CASCADE"), primary_key=True),
)


class Skill(Base):
    __tablename__ = "skill"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
