from sqlalchemy import Table, Column, ForeignKey, Uuid, Integer 
from src.models.base import Base

employee_role = Table(
    "employee_role",
    Base.metadata,
    Column("employee_id", Uuid, ForeignKey("employee.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("role.id", ondelete="CASCADE"), primary_key=True),
)