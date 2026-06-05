from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


class WeekStat(BaseModel):
    week_start: date
    hours: Decimal


class RecentEntry(BaseModel):
    date_from: date
    project_name: Optional[str] = None
    task_name: Optional[str] = None
    spend_time: Decimal


class EmployeeSummaryResponse(BaseModel):
    period_name: str
    logged_hours: Decimal
    norm_hours: Decimal
    utilization_pct: float
    utilization_delta: Optional[float] = None
    remaining_hours: Decimal
    active_projects_count: int
    total_projects_count: int
    avg_weekly_hours: Decimal
    weekly_dynamics: List[WeekStat]
    recent_entries: List[RecentEntry]
