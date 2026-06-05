import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src._access import assert_can_read_employee_data, assert_can_write_employee_data
from src.database import get_async_session
from src.dependencies import get_current_user
from src.schemas.time_entry import TimeEntryCreate, TimeEntryResponse, TimeEntryUpdate
from src.services.time_entry_service import TimeEntryService
from src.services.timesheet_period_service import TimesheetPeriodService

router = APIRouter(prefix="/periods/{period_id}/entries", tags=["Time Entries"])


async def _get_period_or_404(period_id: uuid.UUID, session: AsyncSession):
    svc = TimesheetPeriodService(session)
    period = await svc.get_by_id(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Период не найден")
    return period


@router.get("/", response_model=list[TimeEntryResponse])
async def get_entries(
    period_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    period = await _get_period_or_404(period_id, session)
    await assert_can_read_employee_data(current_user, period.employee_id, session)
    return await TimeEntryService(session).get_all(period_id)


@router.post("/", response_model=TimeEntryResponse, status_code=201)
async def create_entry(
    period_id: uuid.UUID,
    data: TimeEntryCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    period = await _get_period_or_404(period_id, session)
    await assert_can_write_employee_data(current_user, period.employee_id)

    svc = TimeEntryService(session)
    entry, _ = await svc.create(period, data, producer=request.app.state.kafka_producer)
    await session.commit()
    await session.refresh(entry)
    return entry


@router.patch("/{entry_id}", response_model=TimeEntryResponse)
async def update_entry(
    period_id: uuid.UUID,
    entry_id: uuid.UUID,
    data: TimeEntryUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    period = await _get_period_or_404(period_id, session)
    await assert_can_write_employee_data(current_user, period.employee_id)

    svc = TimeEntryService(session)
    entry = await svc.get_by_id(entry_id)
    if not entry or entry.timesheet_period_id != period_id:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    entry = await svc.update(entry, data)
    await session.commit()
    return entry


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(
    period_id: uuid.UUID,
    entry_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    period = await _get_period_or_404(period_id, session)
    await assert_can_write_employee_data(current_user, period.employee_id)

    svc = TimeEntryService(session)
    entry = await svc.get_by_id(entry_id)
    if not entry or entry.timesheet_period_id != period_id:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    await svc.delete(entry)
    await session.commit()
