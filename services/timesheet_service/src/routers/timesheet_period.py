import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src._access import assert_can_read_employee_data
from src.database import get_async_session
from src.dependencies import get_current_user, require_permission
from src.schemas.timesheet_period import TimesheetPeriodResponse
from src.services.timesheet_period_service import TimesheetPeriodService

router = APIRouter(prefix="/periods", tags=["Timesheet Periods"])

_close_period = Depends(require_permission("timesheet:close_period"))


@router.get("/", response_model=list[TimesheetPeriodResponse])
async def get_periods(
    employee_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    svc = TimesheetPeriodService(session)
    perms = set(current_user.get("permissions", []))

    if "timesheet:read_any" in perms:
        # Менеджер/HR/Администратор — видят всё, фильтр по employee_id опционален
        pass
    elif "timesheet:read_team" in perms:
        # Тимлид — только своя команда
        if employee_id:
            await assert_can_read_employee_data(current_user, employee_id, session)
        else:
            return await svc.get_all(
                lead_id=uuid.UUID(current_user["sub"]),
                skip=skip,
                limit=limit,
            )
    else:
        # Сотрудник — только свои
        employee_id = uuid.UUID(current_user["sub"])

    return await svc.get_all(employee_id=employee_id, skip=skip, limit=limit)


@router.get("/{period_id}", response_model=TimesheetPeriodResponse)
async def get_period(
    period_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    svc = TimesheetPeriodService(session)
    period = await svc.get_by_id(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Период не найден")
    await assert_can_read_employee_data(current_user, period.employee_id, session)
    return period


@router.post("/{period_id}/close", response_model=TimesheetPeriodResponse)
async def close_period(
    period_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    payload: dict = _close_period,
):
    svc = TimesheetPeriodService(session)
    period = await svc.close_period(period_id, closed_by=uuid.UUID(payload["sub"]))
    await session.commit()
    return period
