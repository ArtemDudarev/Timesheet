import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src._access import assert_can_read_employee_data
from src.database import get_async_session
from src.dependencies import get_current_user, require_permission
from src.models.employee import Employee
from src.schemas.timesheet_period import TimesheetPeriodReject, TimesheetPeriodResponse
from src.services.timesheet_period_service import TimesheetPeriodService

router = APIRouter(prefix="/periods", tags=["Timesheet Periods"])

_close_period = Depends(require_permission("timesheet:close_period"))
_period_approver = Depends(
    require_permission("timesheet:approve_period", "timesheet:approve_period_team")
)


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


async def _assert_team_access(
    current_user: dict,
    period_id: uuid.UUID,
    svc: TimesheetPeriodService,
    session: AsyncSession,
) -> None:
    perms = set(current_user.get("permissions", []))
    if "timesheet:approve_period" in perms:
        return
    # Тимлид: проверяем что период принадлежит его команде
    period = await svc.get_by_id(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Период не найден")
    emp = await session.get(Employee, period.employee_id)
    if not emp or not emp.lead_id or str(emp.lead_id) != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Сотрудник не в вашей команде")


@router.post("/{period_id}/submit", response_model=TimesheetPeriodResponse)
async def submit_period(
    period_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    svc = TimesheetPeriodService(session)
    period = await svc.get_by_id(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Период не найден")
    if str(period.employee_id) != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Можно отправить только свой период")
    period = await svc.submit_period(period_id, producer=request.app.state.kafka_producer)
    await session.commit()
    return period


@router.post("/{period_id}/approve", response_model=TimesheetPeriodResponse)
async def approve_period(
    period_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = _period_approver,
):
    svc = TimesheetPeriodService(session)
    await _assert_team_access(current_user, period_id, svc, session)
    period = await svc.approve_period(
        period_id,
        approver_id=uuid.UUID(current_user["sub"]),
        producer=request.app.state.kafka_producer,
    )
    await session.commit()
    return period


@router.post("/{period_id}/reject", response_model=TimesheetPeriodResponse)
async def reject_period(
    period_id: uuid.UUID,
    data: TimesheetPeriodReject,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = _period_approver,
):
    svc = TimesheetPeriodService(session)
    await _assert_team_access(current_user, period_id, svc, session)
    period = await svc.reject_period(
        period_id,
        approver_id=uuid.UUID(current_user["sub"]),
        comment=data.comment,
        producer=request.app.state.kafka_producer,
    )
    await session.commit()
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
