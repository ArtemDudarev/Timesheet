from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.production_calendar import DayType, ProductionCalendar
from src.schemas.production_calendar import ProductionCalendarUpsert

STANDARD_HOURS = 8.0
PRE_HOLIDAY_HOURS = 7.0


class ProductionCalendarService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_year(self, year: int) -> list[ProductionCalendar]:
        result = await self.db.execute(
            select(ProductionCalendar).where(
                ProductionCalendar.date >= date(year, 1, 1),
                ProductionCalendar.date <= date(year, 12, 31),
            ).order_by(ProductionCalendar.date)
        )
        return list(result.scalars().all())

    async def upsert(self, data: ProductionCalendarUpsert) -> ProductionCalendar:
        entry = await self.db.get(ProductionCalendar, data.date)
        if entry is None:
            entry = ProductionCalendar(
                date=data.date,
                day_type=data.day_type,
                description=data.description,
            )
            self.db.add(entry)
        else:
            entry.day_type = data.day_type
            entry.description = data.description
        await self.db.flush()
        return entry

    async def get_day_limit(self, day: date) -> float:
        entry = await self.db.get(ProductionCalendar, day)
        if entry is None:
            return STANDARD_HOURS
        if entry.day_type == DayType.PRE_HOLIDAY:
            return PRE_HOLIDAY_HOURS
        if entry.day_type in (DayType.WEEKEND, DayType.HOLIDAY):
            return 0.0
        return STANDARD_HOURS

    async def is_non_working(self, day: date) -> bool:
        entry = await self.db.get(ProductionCalendar, day)
        if entry is None:
            return False
        return entry.day_type in (DayType.WEEKEND, DayType.HOLIDAY)
