import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user, require_roles
from src.schemas.timesheet_period import TimesheetPeriodResponse
from src.services.timesheet_period_service import TimesheetPeriodService

router = APIRouter(prefix="/periods", tags=["Timesheet Periods"])

_manager = Depends(require_roles("Менеджер"))


@router.get("/", response_model=list[TimesheetPeriodResponse])
async def get_periods(
    employee_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
    payload: dict = Depends(get_current_user),
):
    svc = TimesheetPeriodService(session)
    is_manager = "Менеджер" in payload.get("roles", [])
    if not is_manager:
        employee_id = uuid.UUID(payload["sub"])
    return await svc.get_all(employee_id=employee_id, skip=skip, limit=limit)


@router.get("/{period_id}", response_model=TimesheetPeriodResponse)
async def get_period(
    period_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    payload: dict = Depends(get_current_user),
):
    svc = TimesheetPeriodService(session)
    period = await svc.get_by_id(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Период не найден")
    is_manager = "Менеджер" in payload.get("roles", [])
    if not is_manager and str(period.employee_id) != payload["sub"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    return period


@router.post("/{period_id}/close", response_model=TimesheetPeriodResponse)
async def close_period(
    period_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    payload: dict = _manager,
):
    svc = TimesheetPeriodService(session)
    period = await svc.close_period(period_id, closed_by=uuid.UUID(payload["sub"]))
    await session.commit()
    return period
