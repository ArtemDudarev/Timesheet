from sqlalchemy import Column, ForeignKey, Table, Uuid

from .base import Base

role_permission = Table(
    "role_permission",
    Base.metadata,
    Column("role_id", Uuid, ForeignKey("role.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Uuid, ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True),
)
