import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.employee import Employee
from src.models.employee_project import Assignment
from src.models.overtime_approval import ApprovalStatus, OvertimeApproval
from src.models.time_entry import TimeEntry
from src.models.timesheet_period import TimesheetPeriod


class OvertimeApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        status: ApprovalStatus | None = ApprovalStatus.PENDING,
        lead_id: uuid.UUID | None = None,
    ) -> list[OvertimeApproval]:
        q = (
            select(OvertimeApproval)
            # вложенный selectin через identity map не каскадится на asyncpg — грузим явно
            .options(
                selectinload(OvertimeApproval.time_entry)
                .selectinload(TimeEntry.assignment)
                .selectinload(Assignment.project),
                selectinload(OvertimeApproval.time_entry)
                .selectinload(TimeEntry.assignment)
                .selectinload(Assignment.project_role),
            )
            .order_by(OvertimeApproval.created_at)
        )
        if status is not None:
            q = q.where(OvertimeApproval.status == status)
        if lead_id is not None:
            q = (
                q.join(TimeEntry, TimeEntry.id == OvertimeApproval.time_entry_id)
                .join(TimesheetPeriod, TimesheetPeriod.id == TimeEntry.timesheet_period_id)
                .join(Employee, Employee.id == TimesheetPeriod.employee_id)
                .where(Employee.lead_id == lead_id)
            )
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, approval_id: uuid.UUID) -> OvertimeApproval | None:
        return await self.db.get(OvertimeApproval, approval_id)

    async def get_employee_id_for_approval(self, approval: OvertimeApproval) -> uuid.UUID | None:
        entry = await self.db.get(TimeEntry, approval.time_entry_id)
        if not entry:
            return None
        period = await self.db.get(TimesheetPeriod, entry.timesheet_period_id)
        return period.employee_id if period else None

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
