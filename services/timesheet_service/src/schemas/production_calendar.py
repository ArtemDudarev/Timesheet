from datetime import date

from pydantic import BaseModel

from src.models.production_calendar import DayType


class ProductionCalendarUpsert(BaseModel):
    date: date
    day_type: DayType
    description: str | None = None


class ProductionCalendarResponse(BaseModel):
    date: date
    day_type: DayType
    description: str | None

    model_config = {"from_attributes": True}
