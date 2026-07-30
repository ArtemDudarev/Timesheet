import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel


class UtilizationRow(BaseModel):
    employee_id: uuid.UUID
    full_name: str
    logged_hours: float
    norm_hours: float
    utilization_pct: float


class ProjectStatRow(BaseModel):
    project_id: uuid.UUID
    name: str
    client: Optional[str]
    spent_hours: float
    budget_hours: Optional[float]
    progress_pct: Optional[float]
    status: str
    deadline: Optional[date]


class PlanFactRow(BaseModel):
    department_id: uuid.UUID
    department_name: str
    plan_hours: float
    fact_hours: float


class ReportsSummary(BaseModel):
    avg_utilization_pct: float
    total_logged_hours: float
    budget_used_pct: float
    at_risk_projects_count: int
