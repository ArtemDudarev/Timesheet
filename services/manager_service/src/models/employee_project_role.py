from sqlalchemy import Column, ForeignKey, Table, Uuid

from .base import Base


employee_project_role_table = Table(
    "employee_project_role",
    Base.metadata,
    Column(
        "employee_id",
        Uuid,
        ForeignKey("employee.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "project_role_id",
        Uuid,
        ForeignKey("project_role.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
