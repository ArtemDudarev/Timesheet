from sqlalchemy import Column, ForeignKey, Table, Uuid

from .base import Base

user_role = Table(
    "user_role",
    Base.metadata,
    Column("user_id", Uuid, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Uuid, ForeignKey("role.id", ondelete="CASCADE"), primary_key=True),
)
