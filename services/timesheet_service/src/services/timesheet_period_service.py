import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.kafka.events import (
    publish_period_approved,
    publish_period_rejected,
    publish_period_submitted,
)
from src.models.employee import Employee
from src.models.overtime_approval import ApprovalStatus, OvertimeApproval
from src.models.time_entry import TimeEntry
from src.models.timesheet_period import PeriodStatus, SubmissionStatus, TimesheetPeriod


class TimesheetPeriodService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        employee_id: uuid.UUID | None = None,
        lead_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TimesheetPeriod]:
        q = select(TimesheetPeriod)
        if employee_id:
            q = q.where(TimesheetPeriod.employee_id == employee_id)
        elif lead_id:
            # Тимлид видит свои периоды + периоды своей команды
            q = (
                q.join(Employee, Employee.id == TimesheetPeriod.employee_id)
                .where(or_(Employee.lead_id == lead_id, Employee.id == lead_id))
            )
        q = q.order_by(TimesheetPeriod.year.desc(), TimesheetPeriod.month.desc())
        q = q.offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, period_id: uuid.UUID) -> TimesheetPeriod | None:
        return await self.db.get(TimesheetPeriod, period_id)

    async def get_or_create(
        self, employee_id: uuid.UUID, year: int, month: int
    ) -> TimesheetPeriod:
        result = await self.db.execute(
            select(TimesheetPeriod).where(
                TimesheetPeriod.employee_id == employee_id,
                TimesheetPeriod.year == year,
                TimesheetPeriod.month == month,
            )
        )
        period = result.scalar_one_or_none()
        if period is None:
            period = TimesheetPeriod(
                employee_id=employee_id,
                year=year,
                month=month,
                status=PeriodStatus.OPEN,
            )
            self.db.add(period)
            await self.db.flush()
        return period

    async def submit_period(
        self, period_id: uuid.UUID, producer=None
    ) -> TimesheetPeriod:
        period = await self.get_by_id(period_id)
        if not period:
            raise HTTPException(status_code=404, detail="Период не найден")
        if period.status == PeriodStatus.CLOSED:
            raise HTTPException(status_code=409, detail="Период закрыт")
        if period.submission_status in (SubmissionStatus.PENDING, SubmissionStatus.APPROVED):
            raise HTTPException(status_code=409, detail="Период уже отправлен на согласование")

        period.submission_status = SubmissionStatus.PENDING
        period.submitted_at = datetime.utcnow()
        period.approved_by = None
        period.approved_at = None
        period.rejection_comment = None
        await self.db.flush()
        if producer:
            await publish_period_submitted(producer, period)
        return period

    async def approve_period(
        self, period_id: uuid.UUID, approver_id: uuid.UUID, producer=None
    ) -> TimesheetPeriod:
        period = await self.get_by_id(period_id)
        if not period:
            raise HTTPException(status_code=404, detail="Период не найден")
        if period.submission_status != SubmissionStatus.PENDING:
            raise HTTPException(status_code=409, detail="Период не находится на согласовании")

        period.submission_status = SubmissionStatus.APPROVED
        period.approved_by = approver_id
        period.approved_at = datetime.utcnow()
        period.rejection_comment = None
        await self.db.flush()
        if producer:
            await publish_period_approved(producer, period)
        return period

    async def reject_period(
        self, period_id: uuid.UUID, approver_id: uuid.UUID, comment: str, producer=None
    ) -> TimesheetPeriod:
        period = await self.get_by_id(period_id)
        if not period:
            raise HTTPException(status_code=404, detail="Период не найден")
        if period.submission_status != SubmissionStatus.PENDING:
            raise HTTPException(status_code=409, detail="Период не находится на согласовании")

        period.submission_status = SubmissionStatus.REJECTED
        period.approved_by = approver_id
        period.approved_at = datetime.utcnow()
        period.rejection_comment = comment
        await self.db.flush()
        if producer:
            await publish_period_rejected(producer, period)
        return period

    async def close_period(
        self, period_id: uuid.UUID, closed_by: uuid.UUID
    ) -> TimesheetPeriod:
        period = await self.get_by_id(period_id)
        if not period:
            raise HTTPException(status_code=404, detail="Период не найден")
        if period.status == PeriodStatus.CLOSED:
            raise HTTPException(status_code=400, detail="Период уже закрыт")
        if period.submission_status != SubmissionStatus.APPROVED:
            raise HTTPException(status_code=409, detail="Период не согласован")

        # Авто-согласуем все PENDING переработки периода
        entries_result = await self.db.execute(
            select(TimeEntry).where(TimeEntry.timesheet_period_id == period_id)
        )
        entry_ids = [e.id for e in entries_result.scalars().all()]

        if entry_ids:
            approvals_result = await self.db.execute(
                select(OvertimeApproval).where(
                    OvertimeApproval.time_entry_id.in_(entry_ids),
                    OvertimeApproval.status == ApprovalStatus.PENDING,
                )
            )
            for approval in approvals_result.scalars().all():
                approval.status = ApprovalStatus.APPROVED
                approval.approver_id = closed_by
                approval.resolved_at = datetime.utcnow()

        period.status = PeriodStatus.CLOSED
        period.closed_by = closed_by
        period.closed_at = datetime.utcnow()
        await self.db.flush()
        return period

    async def create_year_periods(
        self,
        employee_id: uuid.UUID,
        year: int,
        closed_up_to_month: int | None = None,
    ) -> None:
        for month in range(1, 13):
            result = await self.db.execute(
                select(TimesheetPeriod).where(
                    TimesheetPeriod.employee_id == employee_id,
                    TimesheetPeriod.year == year,
                    TimesheetPeriod.month == month,
                )
            )
            if result.scalar_one_or_none() is not None:
                continue
            period_status = (
                PeriodStatus.CLOSED
                if closed_up_to_month and month <= closed_up_to_month
                else PeriodStatus.OPEN
            )
            # Закрытый период не может быть несогласованным (см. проверку в close_period)
            submission_status = (
                SubmissionStatus.APPROVED
                if period_status == PeriodStatus.CLOSED
                else SubmissionStatus.DRAFT
            )
            self.db.add(
                TimesheetPeriod(
                    employee_id=employee_id,
                    year=year,
                    month=month,
                    status=period_status,
                    submission_status=submission_status,
                )
            )
        await self.db.flush()
