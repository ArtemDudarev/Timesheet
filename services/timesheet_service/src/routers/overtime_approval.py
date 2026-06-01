import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import require_roles
from src.schemas.overtime_approval import OvertimeApprovalResolve, OvertimeApprovalResponse
from src.services.overtime_approval_service import OvertimeApprovalService

router = APIRouter(prefix="/overtime-approvals", tags=["Overtime Approvals"])

_manager = Depends(require_roles("Менеджер"))


@router.get("/", response_model=list[OvertimeApprovalResponse])
async def get_pending_approvals(
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    svc = OvertimeApprovalService(session)
    return await svc.get_pending()


@router.post("/{approval_id}/approve", response_model=OvertimeApprovalResponse)
async def approve(
    approval_id: uuid.UUID,
    data: OvertimeApprovalResolve,
    session: AsyncSession = Depends(get_async_session),
    payload: dict = _manager,
):
    svc = OvertimeApprovalService(session)
    approval = await svc.approve(approval_id, uuid.UUID(payload["sub"]), data.comment)
    await session.commit()
    return approval


@router.post("/{approval_id}/reject", response_model=OvertimeApprovalResponse)
async def reject(
    approval_id: uuid.UUID,
    data: OvertimeApprovalResolve,
    session: AsyncSession = Depends(get_async_session),
    payload: dict = _manager,
):
    svc = OvertimeApprovalService(session)
    approval = await svc.reject(approval_id, uuid.UUID(payload["sub"]), data.comment)
    await session.commit()
    return approval
