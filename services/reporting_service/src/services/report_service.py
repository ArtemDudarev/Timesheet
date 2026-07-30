import calendar
import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.department import Department
from src.models.department_plan import DepartmentPlan
from src.models.employee import Employee
from src.models.project import Project
from src.models.time_entry_replica import TimeEntryReplica
from src.schemas.report import PlanFactRow, ProjectStatRow, ReportsSummary, UtilizationRow

STANDARD_HOURS = 8

# Учитываем как отработанные только фактическую работу и переработки —
# больничные/отпуска не считаются загрузкой
LOGGED_TYPE_CODES = ("WORK", "OVERTIME")

# Статусы, при которых просроченный дедлайн не считается риском
FINISHED_STATUSES = ("Завершён", "Архивный")


def parse_period(period: str) -> tuple[int, int]:
    try:
        year_str, month_str = period.split("-")
        year, month = int(year_str), int(month_str)
        if not 1 <= month <= 12:
            raise ValueError
        return year, month
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail="period должен быть в формате YYYY-MM")


def month_norm_hours(year: int, month: int) -> float:
    """Норма часов месяца: рабочие дни (пн-пт) × 8.

    Приближение — праздники не учитываются: производственный календарь
    живёт в timesheet_service и в reporting не реплицируется (см. открытые вопросы).
    """
    days_in_month = calendar.monthrange(year, month)[1]
    workdays = sum(
        1 for d in range(1, days_in_month + 1)
        if date(year, month, d).weekday() < 5
    )
    return float(workdays * STANDARD_HOURS)


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def utilization(self, period: str) -> list[UtilizationRow]:
        year, month = parse_period(period)
        norm = month_norm_hours(year, month)

        logged_sq = (
            select(
                TimeEntryReplica.employee_id,
                func.coalesce(func.sum(TimeEntryReplica.spend_time), 0).label("logged"),
            )
            .where(
                TimeEntryReplica.year == year,
                TimeEntryReplica.month == month,
                TimeEntryReplica.type_code.in_(LOGGED_TYPE_CODES),
            )
            .group_by(TimeEntryReplica.employee_id)
            .subquery()
        )
        result = await self.db.execute(
            select(Employee, func.coalesce(logged_sq.c.logged, 0))
            .outerjoin(logged_sq, logged_sq.c.employee_id == Employee.id)
            .order_by(Employee.last_name, Employee.first_name)
        )
        rows = []
        for employee, logged in result.all():
            logged = float(logged)
            rows.append(UtilizationRow(
                employee_id=employee.id,
                full_name=f"{employee.first_name} {employee.last_name}",
                logged_hours=logged,
                norm_hours=norm,
                utilization_pct=round(logged / norm * 100, 1) if norm else 0.0,
            ))
        return rows

    async def projects(self, period: str) -> list[ProjectStatRow]:
        year, month = parse_period(period)
        spent_sq = (
            select(
                TimeEntryReplica.project_id,
                func.coalesce(func.sum(TimeEntryReplica.spend_time), 0).label("spent"),
            )
            .where(
                TimeEntryReplica.year == year,
                TimeEntryReplica.month == month,
                TimeEntryReplica.project_id.is_not(None),
            )
            .group_by(TimeEntryReplica.project_id)
            .subquery()
        )
        result = await self.db.execute(
            select(Project, func.coalesce(spent_sq.c.spent, 0))
            .outerjoin(spent_sq, spent_sq.c.project_id == Project.id)
            .order_by(Project.name)
        )
        rows = []
        for project, spent in result.all():
            spent = float(spent)
            budget = float(project.budget_hours) if project.budget_hours is not None else None
            rows.append(ProjectStatRow(
                project_id=project.id,
                name=project.name,
                client=project.client,
                spent_hours=spent,
                budget_hours=budget,
                progress_pct=round(spent / budget * 100, 1) if budget else None,
                status=project.status or "—",
                deadline=project.deadline,
            ))
        return rows

    async def plan_fact(self, period: str) -> list[PlanFactRow]:
        year, month = parse_period(period)

        fact_sq = (
            select(
                Employee.department_id,
                func.coalesce(func.sum(TimeEntryReplica.spend_time), 0).label("fact"),
            )
            .join(TimeEntryReplica, TimeEntryReplica.employee_id == Employee.id)
            .where(
                TimeEntryReplica.year == year,
                TimeEntryReplica.month == month,
                TimeEntryReplica.type_code.in_(LOGGED_TYPE_CODES),
                Employee.department_id.is_not(None),
            )
            .group_by(Employee.department_id)
            .subquery()
        )
        plan_sq = (
            select(DepartmentPlan.department_id, DepartmentPlan.planned_hours)
            .where(DepartmentPlan.year == year, DepartmentPlan.month == month)
            .subquery()
        )
        result = await self.db.execute(
            select(
                Department,
                func.coalesce(plan_sq.c.planned_hours, 0),
                func.coalesce(fact_sq.c.fact, 0),
            )
            .outerjoin(plan_sq, plan_sq.c.department_id == Department.id)
            .outerjoin(fact_sq, fact_sq.c.department_id == Department.id)
            .order_by(Department.name)
        )
        return [
            PlanFactRow(
                department_id=dept.id,
                department_name=dept.name,
                plan_hours=float(plan),
                fact_hours=float(fact),
            )
            for dept, plan, fact in result.all()
        ]

    async def summary(self, period: str) -> ReportsSummary:
        utilization_rows = await self.utilization(period)
        project_rows = await self.projects(period)

        with_norm = [r for r in utilization_rows if r.norm_hours > 0]
        avg_utilization = (
            round(sum(r.utilization_pct for r in with_norm) / len(with_norm), 1)
            if with_norm else 0.0
        )
        total_logged = sum(r.logged_hours for r in utilization_rows)

        budgeted = [r for r in project_rows if r.budget_hours]
        total_budget = sum(r.budget_hours for r in budgeted)
        total_spent_on_budgeted = sum(r.spent_hours for r in budgeted)
        budget_used_pct = (
            round(total_spent_on_budgeted / total_budget * 100, 1) if total_budget else 0.0
        )

        return ReportsSummary(
            avg_utilization_pct=avg_utilization,
            total_logged_hours=total_logged,
            budget_used_pct=budget_used_pct,
            at_risk_projects_count=sum(1 for r in project_rows if self._is_at_risk(r)),
        )

    @staticmethod
    def _is_at_risk(row: ProjectStatRow) -> bool:
        """«Под риском» — рабочее определение (вопрос №5 контракта не решён продуктово):
        перерасход бюджета часов ИЛИ просроченный дедлайн у незавершённого проекта."""
        over_budget = row.budget_hours is not None and row.spent_hours > row.budget_hours
        overdue = (
            row.deadline is not None
            and row.deadline < date.today()
            and row.status not in FINISHED_STATUSES
        )
        return over_budget or overdue
