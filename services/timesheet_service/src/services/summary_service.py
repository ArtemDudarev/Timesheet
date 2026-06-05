import uuid
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.employee_project import Assignment
from src.models.production_calendar import DayType, ProductionCalendar
from src.models.time_entry import TimeEntry
from src.models.timesheet_period import TimesheetPeriod
from src.schemas.summary import EmployeeSummaryResponse, RecentEntry, WeekStat
from src.services.production_calendar_service import PRE_HOLIDAY_HOURS, STANDARD_HOURS
from src.services.timesheet_period_service import TimesheetPeriodService

_MONTH_NAMES = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]


class SummaryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary(
        self,
        employee_id: uuid.UUID,
        year: int,
        month: int,
    ) -> EmployeeSummaryResponse:
        period_svc = TimesheetPeriodService(self.db)
        period = await period_svc.get_or_create(employee_id, year, month)

        norm = await self._calc_norm(year, month)
        logged = self._sum_entries(period.entries)
        utilization_pct = float(logged / norm * 100) if norm else 0.0
        remaining = max(Decimal("0"), norm - logged)

        prev_delta = await self._prev_utilization_delta(
            employee_id, year, month, norm, utilization_pct
        )

        active_count, total_count = await self._project_counts(employee_id)
        weekly = await self._weekly_dynamics(employee_id)
        avg_weekly = (
            sum(w.hours for w in weekly) / len(weekly)
            if weekly else Decimal("0")
        )
        recent = await self._recent_entries(employee_id)

        return EmployeeSummaryResponse(
            period_name=f"{_MONTH_NAMES[month]} {year}",
            logged_hours=logged,
            norm_hours=norm,
            utilization_pct=round(utilization_pct, 1),
            utilization_delta=prev_delta,
            remaining_hours=remaining,
            active_projects_count=active_count,
            total_projects_count=total_count,
            avg_weekly_hours=round(avg_weekly, 1),
            weekly_dynamics=weekly,
            recent_entries=recent,
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    async def _calc_norm(self, year: int, month: int) -> Decimal:
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        result = await self.db.execute(
            select(ProductionCalendar).where(
                ProductionCalendar.date >= first_day,
                ProductionCalendar.date <= last_day,
            )
        )
        calendar_map = {row.date: row for row in result.scalars().all()}

        total = Decimal("0")
        current = first_day
        while current <= last_day:
            entry = calendar_map.get(current)
            if entry is None:
                # нет записи в календаре — стандартный рабочий день
                if current.weekday() < 5:
                    total += Decimal(str(STANDARD_HOURS))
            elif entry.day_type == DayType.PRE_HOLIDAY:
                total += Decimal(str(PRE_HOLIDAY_HOURS))
            elif entry.day_type not in (DayType.WEEKEND, DayType.HOLIDAY):
                total += Decimal(str(STANDARD_HOURS))
            current += timedelta(days=1)
        return total

    def _sum_entries(self, entries) -> Decimal:
        return sum((e.spend_time for e in entries), Decimal("0"))

    async def _prev_utilization_delta(
        self,
        employee_id: uuid.UUID,
        year: int,
        month: int,
        current_norm: Decimal,
        current_pct: float,
    ) -> Optional[float]:
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1

        result = await self.db.execute(
            select(TimesheetPeriod).where(
                TimesheetPeriod.employee_id == employee_id,
                TimesheetPeriod.year == prev_year,
                TimesheetPeriod.month == prev_month,
            )
        )
        prev_period = result.scalar_one_or_none()
        if prev_period is None:
            return None

        prev_norm = await self._calc_norm(prev_year, prev_month)
        if not prev_norm:
            return None

        prev_logged = self._sum_entries(prev_period.entries)
        prev_pct = float(prev_logged / prev_norm * 100)
        return round(current_pct - prev_pct, 1)

    async def _project_counts(self, employee_id: uuid.UUID):
        result = await self.db.execute(
            select(Assignment).where(Assignment.employee_id == employee_id)
        )
        assignments = result.scalars().all()
        total = len(assignments)
        active = sum(1 for a in assignments if a.status == "ACTIVE")
        return active, total

    async def _weekly_dynamics(self, employee_id: uuid.UUID):
        cutoff = date.today() - timedelta(weeks=8)
        result = await self.db.execute(
            select(TimeEntry).where(
                TimeEntry.employee_id == employee_id,
                TimeEntry.date_from >= cutoff,
            )
        )
        entries = result.scalars().all()

        weeks: dict[date, Decimal] = {}
        for entry in entries:
            week_start = entry.date_from - timedelta(days=entry.date_from.weekday())
            weeks[week_start] = weeks.get(week_start, Decimal("0")) + entry.spend_time

        return [
            WeekStat(week_start=ws, hours=hours)
            for ws, hours in sorted(weeks.items())
        ]

    async def _recent_entries(self, employee_id: uuid.UUID):
        result = await self.db.execute(
            select(TimeEntry)
            .where(TimeEntry.employee_id == employee_id)
            .order_by(TimeEntry.date_from.desc())
            .limit(10)
        )
        entries = result.scalars().all()

        recent = []
        for entry in entries:
            project_name: Optional[str] = None
            if entry.assignment and entry.assignment.project:
                project_name = entry.assignment.project.name
            recent.append(RecentEntry(
                date_from=entry.date_from,
                project_name=project_name,
                task_name=entry.task_name,
                spend_time=entry.spend_time,
            ))
        return recent
