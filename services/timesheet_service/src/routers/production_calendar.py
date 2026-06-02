from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user, require_roles
from src.schemas.production_calendar import ProductionCalendarResponse, ProductionCalendarUpsert
from src.services.production_calendar_service import ProductionCalendarService

router = APIRouter(prefix="/production-calendar", tags=["Production Calendar"])

_authenticated = Depends(get_current_user)
_manager = Depends(require_roles("Менеджер"))


@router.get("/{year}", response_model=list[ProductionCalendarResponse])
async def get_calendar(
    year: int,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _authenticated,
):
    svc = ProductionCalendarService(session)
    return await svc.get_by_year(year)


@router.post("/", response_model=ProductionCalendarResponse, status_code=201)
async def upsert_calendar_entry(
    data: ProductionCalendarUpsert,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    svc = ProductionCalendarService(session)
    entry = await svc.upsert(data)
    await session.commit()
    return entry
