import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.overtime_approval import ApprovalStatus, OvertimeApproval


class OvertimeApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_pending(self) -> list[OvertimeApproval]:
        result = await self.db.execute(
            select(OvertimeApproval)
            .where(OvertimeApproval.status == ApprovalStatus.PENDING)
            .order_by(OvertimeApproval.created_at)
        )
        return list(result.scalars().all())

    async def get_by_id(self, approval_id: uuid.UUID) -> OvertimeApproval | None:
        return await self.db.get(OvertimeApproval, approval_id)

    async def approve(
        self, approval_id: uuid.UUID, approver_id: uuid.UUID, comment: str | None
    ) -> OvertimeApproval:
        approval = await self.get_by_id(approval_id)
        if not approval:
            raise HTTPException(status_code=404, detail="Согласование не найдено")
        if approval.status != ApprovalStatus.PENDING:
            raise HTTPException(status_code=400, detail="Согласование уже завершено")
        approval.status = ApprovalStatus.APPROVED
        approval.approver_id = approver_id
        approval.comment = comment
        approval.resolved_at = datetime.utcnow()
        await self.db.flush()
        return approval

    async def reject(
        self, approval_id: uuid.UUID, approver_id: uuid.UUID, comment: str | None
    ) -> OvertimeApproval:
        approval = await self.get_by_id(approval_id)
        if not approval:
            raise HTTPException(status_code=404, detail="Согласование не найдено")
        if approval.status != ApprovalStatus.PENDING:
            raise HTTPException(status_code=400, detail="Согласование уже завершено")
        approval.status = ApprovalStatus.REJECTED
        approval.approver_id = approver_id
        approval.comment = comment
        approval.resolved_at = datetime.utcnow()
        await self.db.flush()
        return approval
