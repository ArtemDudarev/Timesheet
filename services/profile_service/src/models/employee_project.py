from sqlalchemy import Table, Column, ForeignKey, Uuid, Integer 
from src.models.base import Base

employee_project = Table(
    "employee_project",
    Base.metadata,

    Column(
        "employee_id",
        Uuid,
        ForeignKey("employee.employee_id", ondelete="CASCADE"),
        primary_key=True
    ),

    Column(
        "project_id",
        Uuid,
        ForeignKey("project.id", ondelete="CASCADE"),
        primary_key=True
    ),
)