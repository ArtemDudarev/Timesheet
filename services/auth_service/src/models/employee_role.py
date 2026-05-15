from sqlalchemy import Table, Column, ForeignKey, Uuid 
from .base import Base

employee_role = Table(
    "employee_role",
    Base.metadata,
    Column("employee_id", Uuid, ForeignKey("employee.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Uuid, ForeignKey("role.id", ondelete="CASCADE"), primary_key=True),
)