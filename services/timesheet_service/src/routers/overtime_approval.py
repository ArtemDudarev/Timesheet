import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user, require_permission
from src.models.employee import Employee
from src.schemas.overtime_approval import OvertimeApprovalResolve, OvertimeApprovalResponse
from src.services.overtime_approval_service import OvertimeApprovalService

router = APIRouter(prefix="/overtime-approvals", tags=["Overtime Approvals"])

_approver = Depends(require_permission("overtime:approve", "overtime:approve_team"))


@router.get("/", response_model=list[OvertimeApprovalResponse])
async def get_pending_approvals(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = _approver,
):
    svc = OvertimeApprovalService(session)
    perms = set(current_user.get("permissions", []))
    # Тимлид с только командным правом видит только свою команду
    lead_id = None if "overtime:approve" in perms else uuid.UUID(current_user["sub"])
    return await svc.get_pending(lead_id=lead_id)


async def _assert_team_access(
    current_user: dict,
    approval_id: uuid.UUID,
    svc: OvertimeApprovalService,
    session: AsyncSession,
) -> None:
    perms = set(current_user.get("permissions", []))
    if "overtime:approve" in perms:
        return
    # Тимлид: проверяем что запись принадлежит его команде
    approval = await svc.get_by_id(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Согласование не найдено")
    employee_id = await svc.get_employee_id_for_approval(approval)
    if employee_id is None:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    emp = await session.get(Employee, employee_id)
    if not emp or not emp.lead_id or str(emp.lead_id) != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Сотрудник не в вашей команде")


@router.post("/{approval_id}/approve", response_model=OvertimeApprovalResponse)
async def approve(
    approval_id: uuid.UUID,
    data: OvertimeApprovalResolve,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = _approver,
):
    svc = OvertimeApprovalService(session)
    await _assert_team_access(current_user, approval_id, svc, session)
    approval = await svc.approve(approval_id, uuid.UUID(current_user["sub"]), data.comment)
    await session.commit()
    return approval


@router.post("/{approval_id}/reject", response_model=OvertimeApprovalResponse)
async def reject(
    approval_id: uuid.UUID,
    data: OvertimeApprovalResolve,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = _approver,
):
    svc = OvertimeApprovalService(session)
    await _assert_team_access(current_user, approval_id, svc, session)
    approval = await svc.reject(approval_id, uuid.UUID(current_user["sub"]), data.comment)
    await session.commit()
    return approval
