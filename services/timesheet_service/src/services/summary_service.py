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
        remaining = max(Decimal("0"), norm - logged)

        # utilization_pct = "Загрузка" (донат в шапке профиля) — темп ТЕКУЩЕГО месяца.
        # Для текущего месяца норма берётся не целиком, а "на сегодня" — иначе 1-го числа
        # при полной загрузке показатель был бы 5-10%. Для прошлых месяцев — норма целиком.
        today = date.today()
        if (year, month) == (today.year, today.month):
            elapsed_norm = await self._calc_norm(year, month, upto=today)
        else:
            elapsed_norm = norm
        utilization_pct = float(logged / elapsed_norm * 100) if elapsed_norm else 0.0

        # "Утилизация" — отдельная от текущей "загрузки" метрика: всегда за прошлый ЗАВЕРШЁННЫЙ
        # месяц (без шума от неполного текущего месяца), с трендом относительно позапрошлого
        prev_month, prev_year = (month - 1, year) if month > 1 else (12, year - 1)
        prev2_month, prev2_year = (
            (prev_month - 1, prev_year) if prev_month > 1 else (12, prev_year - 1)
        )
        prev_month_pct = await self._month_utilization(employee_id, prev_year, prev_month)
        prev2_month_pct = await self._month_utilization(employee_id, prev2_year, prev2_month)
        utilization_delta = (
            round(prev_month_pct - prev2_month_pct, 1)
            if prev_month_pct is not None and prev2_month_pct is not None
            else None
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
            prev_month_utilization_pct=(
                round(prev_month_pct, 1) if prev_month_pct is not None else None
            ),
            utilization_delta=utilization_delta,
            remaining_hours=remaining,
            active_projects_count=active_count,
            total_projects_count=total_count,
            avg_weekly_hours=round(avg_weekly, 1),
            weekly_dynamics=weekly,
            recent_entries=recent,
        )

    # ── helpers ───────────────────────────────────────────────────────────────

    async def _calc_norm(self, year: int, month: int, upto: Optional[date] = None) -> Decimal:
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])
        if upto is not None and upto < last_day:
            last_day = upto

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

    async def _month_utilization(
        self, employee_id: uuid.UUID, year: int, month: int
    ) -> Optional[float]:
        """Утилизация за ЗАВЕРШЁННЫЙ месяц — всегда от полной нормы (месяц уже прошёл
        целиком, поэтому "на сегодня" здесь не имеет смысла)."""
        result = await self.db.execute(
            select(TimesheetPeriod).where(
                TimesheetPeriod.employee_id == employee_id,
                TimesheetPeriod.year == year,
                TimesheetPeriod.month == month,
            )
        )
        period = result.scalar_one_or_none()
        if period is None:
            return None

        norm = await self._calc_norm(year, month)
        if not norm:
            return None

        logged = self._sum_entries(period.entries)
        return float(logged / norm * 100)

    async def _project_counts(self, employee_id: uuid.UUID):
        # "Активных" — по статусу самого ПРОЕКТА (project.status_code == ACTIVE), а не по
        # статусу назначения сотрудника: сотрудник может быть привлечён (ACTIVE-назначение)
        # к проекту, который сам ещё в статусе "Планируется"
        result = await self.db.execute(
            select(Assignment).where(Assignment.employee_id == employee_id)
        )
        assignments = result.scalars().all()
        projects = {a.project_id: a.project for a in assignments}
        total = len(projects)
        active = sum(1 for p in projects.values() if p.status_code == "ACTIVE")
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
