import logging
from datetime import date, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.entry_type_ref import EntryTypeRef
from src.models.production_calendar import DayType, ProductionCalendar
from src.models.timesheet_period import PeriodStatus, TimesheetPeriod
from src.models.employee import Employee
from sqlalchemy import select

logger = logging.getLogger(__name__)

XMLCALENDAR_URL = "https://xmlcalendar.ru/data/ru/{year}/calendar.json"

ENTRY_TYPES = [
    ("WORK",       "Работа",       "Рабочие часы в рамках проекта"),
    ("OVERTIME",   "Переработка",  "Сверхурочные часы сверх дневного лимита"),
    ("SICK_LEAVE", "Больничный",   "Временная нетрудоспособность"),
    ("VACATION",   "Отпуск",       "Ежегодный оплачиваемый отпуск"),
]

# Фолбэк на случай недоступности API
_FALLBACK: dict[int, list[tuple[date, DayType, str | None]]] = {
    2025: [
        (date(2025, 1, 1), DayType.HOLIDAY, "Новый год"),
        (date(2025, 1, 2), DayType.HOLIDAY, "Новогодние каникулы"),
        (date(2025, 1, 3), DayType.HOLIDAY, "Новогодние каникулы"),
        (date(2025, 1, 6), DayType.HOLIDAY, "Новогодние каникулы"),
        (date(2025, 1, 7), DayType.HOLIDAY, "Рождество Христово"),
        (date(2025, 1, 8), DayType.HOLIDAY, "Новогодние каникулы"),
        (date(2025, 1, 9), DayType.PRE_HOLIDAY, "Предпраздничный день"),
        (date(2025, 2, 24), DayType.HOLIDAY, "День защитника Отечества (перенос)"),
        (date(2025, 3, 7), DayType.PRE_HOLIDAY, "Предпраздничный день"),
        (date(2025, 3, 10), DayType.HOLIDAY, "Международный женский день (перенос)"),
        (date(2025, 4, 30), DayType.PRE_HOLIDAY, "Предпраздничный день"),
        (date(2025, 5, 1), DayType.HOLIDAY, "Праздник Весны и Труда"),
        (date(2025, 5, 2), DayType.HOLIDAY, "Праздник Весны и Труда (перенос)"),
        (date(2025, 5, 8), DayType.HOLIDAY, "День Победы (перенос)"),
        (date(2025, 5, 9), DayType.HOLIDAY, "День Победы"),
        (date(2025, 6, 12), DayType.HOLIDAY, "День России"),
        (date(2025, 6, 13), DayType.HOLIDAY, "День России (перенос)"),
        (date(2025, 11, 3), DayType.PRE_HOLIDAY, "Предпраздничный день"),
        (date(2025, 11, 4), DayType.HOLIDAY, "День народного единства"),
        (date(2025, 12, 31), DayType.HOLIDAY, "Новогодние каникулы (перенос)"),
    ],
    2026: [
        (date(2026, 1, 1), DayType.HOLIDAY, "Новый год"),
        (date(2026, 1, 2), DayType.HOLIDAY, "Новогодние каникулы"),
        (date(2026, 1, 5), DayType.HOLIDAY, "Новогодние каникулы"),
        (date(2026, 1, 6), DayType.HOLIDAY, "Новогодние каникулы"),
        (date(2026, 1, 7), DayType.HOLIDAY, "Рождество Христово"),
        (date(2026, 1, 8), DayType.HOLIDAY, "Новогодние каникулы"),
        (date(2026, 1, 9), DayType.HOLIDAY, "Новогодние каникулы"),
        (date(2026, 2, 23), DayType.HOLIDAY, "День защитника Отечества"),
        (date(2026, 3, 9), DayType.HOLIDAY, "Международный женский день (перенос)"),
        (date(2026, 5, 1), DayType.HOLIDAY, "Праздник Весны и Труда"),
        (date(2026, 5, 4), DayType.HOLIDAY, "Праздник Весны и Труда (перенос)"),
        (date(2026, 5, 11), DayType.HOLIDAY, "День Победы (перенос)"),
        (date(2026, 6, 12), DayType.HOLIDAY, "День России"),
        (date(2026, 11, 4), DayType.HOLIDAY, "День народного единства"),
    ],
}


async def seed_entry_types(session_maker: async_sessionmaker) -> None:
    async with session_maker() as session:
        for code, name, description in ENTRY_TYPES:
            result = await session.execute(
                select(EntryTypeRef).where(EntryTypeRef.code == code)
            )
            if result.scalar_one_or_none() is None:
                session.add(EntryTypeRef(code=code, name=name, description=description))
        await session.commit()
    logger.info("Entry types seeded")


async def _fetch_year_from_api(year: int) -> list[tuple[date, DayType, str | None]]:
    url = XMLCALENDAR_URL.format(year=year)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        logger.warning("Не удалось загрузить календарь за %d из API: %s", year, exc)
        return []

    holidays_map: dict[str, str] = {
        str(h["id"]): h["title"] for h in data.get("holidays", [])
    }

    result: list[tuple[date, DayType, str | None]] = []
    for month_data in data.get("months", []):
        month_num = int(month_data["month"])
        for raw in month_data.get("days", "").split(","):
            raw = raw.strip()
            if not raw:
                continue

            if raw.endswith("*"):
                # Предпраздничный (сокращённый) день
                day_num = int(raw[:-1])
                result.append((
                    date(year, month_num, day_num),
                    DayType.PRE_HOLIDAY,
                    "Предпраздничный день",
                ))
            elif raw.endswith("+"):
                # Рабочая суббота (перенос) — рабочий день, в таблицу не вносим
                pass
            else:
                # Праздник / выходной; возможен суффикс @holiday_id
                if "@" in raw:
                    day_part, holiday_id = raw.split("@", 1)
                    day_num = int(day_part)
                    description = holidays_map.get(holiday_id)
                else:
                    day_num = int(raw)
                    description = None
                result.append((
                    date(year, month_num, day_num),
                    DayType.HOLIDAY,
                    description,
                ))

    return result


async def seed_production_calendar(session_maker: async_sessionmaker) -> None:
    now_year = datetime.utcnow().year
    years_to_seed = [now_year, now_year + 1]

    async with session_maker() as session:
        for year in years_to_seed:
            entries = await _fetch_year_from_api(year)

            if entries:
                logger.info("Календарь за %d загружен из API (%d записей)", year, len(entries))
            else:
                entries = _FALLBACK.get(year, [])
                if entries:
                    logger.warning("Используем фолбэк-данные для календаря за %d", year)
                else:
                    logger.warning("Нет данных для календаря за %d", year)

            for day_date, day_type, description in entries:
                existing = await session.get(ProductionCalendar, day_date)
                if existing is None:
                    session.add(ProductionCalendar(
                        date=day_date,
                        day_type=day_type,
                        description=description,
                    ))

        await session.commit()
    logger.info("Производственный календарь заполнен")


async def seed_existing_employee_periods(session_maker: async_sessionmaker) -> None:
    """При первом деплое создаём периоды для всех сотрудников:
    прошлые месяцы текущего года — CLOSED, будущие — OPEN."""
    now = datetime.utcnow()
    year = now.year
    current_month = now.month

    async with session_maker() as session:
        result = await session.execute(select(Employee))
        employees = result.scalars().all()

        for employee in employees:
            for month in range(1, 13):
                existing = await session.execute(
                    select(TimesheetPeriod).where(
                        TimesheetPeriod.employee_id == employee.id,
                        TimesheetPeriod.year == year,
                        TimesheetPeriod.month == month,
                    )
                )
                if existing.scalar_one_or_none() is not None:
                    continue
                period_status = (
                    PeriodStatus.CLOSED if month < current_month else PeriodStatus.OPEN
                )
                session.add(TimesheetPeriod(
                    employee_id=employee.id,
                    year=year,
                    month=month,
                    status=period_status,
                ))
        await session.commit()
    logger.info("Employee periods seeded")
