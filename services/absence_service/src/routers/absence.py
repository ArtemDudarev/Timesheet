import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user, require_permission
from src.kafka.events import (
    publish_absence_created,
    publish_absence_status_changed,
    publish_absence_updated,
)
from src.models.absence import Absence, AbsenceStatus
from src.models.employee import Employee
from src.schemas.absence import (
    AbsenceApprove,
    AbsenceCreate,
    AbsenceRead,
    AbsenceReject,
    AbsenceUpdate,
)
from src.services.absence_service import AbsenceService

router = APIRouter(prefix="/absences", tags=["Absences"])

_approver = Depends(require_permission("absence:approve", "absence:approve_team"))


async def _assert_can_read(current_user: dict, employee_id: uuid.UUID, session: AsyncSession) -> None:
    if str(employee_id) == current_user["sub"]:
        return
    perms = set(current_user.get("permissions", []))
    if "absence:read_any" in perms:
        return
    if "absence:read_team" in perms:
        emp = await session.get(Employee, employee_id)
        if emp and emp.lead_id and str(emp.lead_id) == current_user["sub"]:
            return
    raise HTTPException(status_code=403, detail="Нет доступа к заявкам этого сотрудника")


async def _assert_team_access(current_user: dict, absence: Absence, session: AsyncSession) -> None:
    perms = set(current_user.get("permissions", []))
    if "absence:approve" in perms:
        return
    # Тимлид: только своя команда
    emp = await session.get(Employee, absence.employee_id)
    if not emp or not emp.lead_id or str(emp.lead_id) != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Сотрудник не в вашей команде")


async def _get_absence_or_404(absence_id: uuid.UUID, session: AsyncSession) -> Absence:
    absence = await AbsenceService(session).get_by_id(absence_id)
    if not absence:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return absence


@router.get("/", response_model=list[AbsenceRead])
async def get_absences(
    employee_id: uuid.UUID | None = None,
    status_filter: AbsenceStatus | None = Query(None, alias="status"),
    type_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    svc = AbsenceService(session)
    perms = set(current_user.get("permissions", []))

    if "absence:read_any" in perms:
        pass  # фильтр по employee_id опционален
    elif "absence:read_team" in perms:
        if employee_id:
            await _assert_can_read(current_user, employee_id, session)
        else:
            return await svc.get_all(
                lead_id=uuid.UUID(current_user["sub"]),
                status=status_filter,
                type_id=type_id,
                skip=skip,
                limit=limit,
            )
    else:
        employee_id = uuid.UUID(current_user["sub"])

    return await svc.get_all(
        employee_id=employee_id, status=status_filter, type_id=type_id, skip=skip, limit=limit
    )


@router.get("/{absence_id}", response_model=AbsenceRead)
async def get_absence(
    absence_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    absence = await _get_absence_or_404(absence_id, session)
    await _assert_can_read(current_user, absence.employee_id, session)
    return absence


@router.post("/", response_model=AbsenceRead, status_code=status.HTTP_201_CREATED)
async def create_absence(
    data: AbsenceCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    svc = AbsenceService(session)
    absence = await svc.create(uuid.UUID(current_user["sub"]), data)
    await publish_absence_created(request.app.state.kafka_producer, absence)
    if absence.status == AbsenceStatus.PENDING:
        await publish_absence_status_changed(request.app.state.kafka_producer, absence)
    await session.commit()
    return absence


@router.patch("/{absence_id}", response_model=AbsenceRead)
async def update_absence(
    absence_id: uuid.UUID,
    data: AbsenceUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    absence = await _get_absence_or_404(absence_id, session)
    if str(absence.employee_id) != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Можно изменять только свою заявку")
    absence = await AbsenceService(session).update(absence, data)
    await publish_absence_updated(request.app.state.kafka_producer, absence)
    await session.commit()
    return absence


@router.delete("/{absence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw_absence(
    absence_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    absence = await _get_absence_or_404(absence_id, session)
    if str(absence.employee_id) != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Можно отозвать только свою заявку")
    result = await AbsenceService(session).withdraw(absence)
    if result is not None:  # PENDING → CANCELLED
        await publish_absence_status_changed(request.app.state.kafka_producer, result)
    await session.commit()


@router.post("/{absence_id}/submit", response_model=AbsenceRead)
async def submit_absence(
    absence_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    absence = await _get_absence_or_404(absence_id, session)
    if str(absence.employee_id) != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Можно отправить только свою заявку")
    absence = await AbsenceService(session).submit(absence)
    await publish_absence_status_changed(request.app.state.kafka_producer, absence)
    await session.commit()
    return absence


@router.post("/{absence_id}/approve", response_model=AbsenceRead)
async def approve_absence(
    absence_id: uuid.UUID,
    data: AbsenceApprove,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = _approver,
):
    absence = await _get_absence_or_404(absence_id, session)
    await _assert_team_access(current_user, absence, session)
    absence = await AbsenceService(session).approve(absence, uuid.UUID(current_user["sub"]))
    await publish_absence_status_changed(request.app.state.kafka_producer, absence)
    await session.commit()
    return absence


@router.post("/{absence_id}/reject", response_model=AbsenceRead)
async def reject_absence(
    absence_id: uuid.UUID,
    data: AbsenceReject,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = _approver,
):
    absence = await _get_absence_or_404(absence_id, session)
    await _assert_team_access(current_user, absence, session)
    absence = await AbsenceService(session).reject(
        absence, uuid.UUID(current_user["sub"]), data.comment
    )
    await publish_absence_status_changed(request.app.state.kafka_producer, absence)
    await session.commit()
    return absence
