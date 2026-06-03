import uuid
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.employee_project import Assignment
from src.models.entry_type_ref import EntryTypeRef
from src.models.overtime_approval import ApprovalStatus, OvertimeApproval
from src.models.time_entry import TimeEntry
from src.models.timesheet_period import PeriodStatus, TimesheetPeriod
from src.schemas.time_entry import TimeEntryCreate, TimeEntryUpdate
from src.services.production_calendar_service import (
    STANDARD_HOURS,
    ProductionCalendarService,
)

WORK = "WORK"
OVERTIME = "OVERTIME"
SICK_LEAVE = "SICK_LEAVE"
VACATION = "VACATION"


class TimeEntryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.calendar_svc = ProductionCalendarService(db)

    async def get_all(self, period_id: uuid.UUID) -> list[TimeEntry]:
        result = await self.db.execute(
            select(TimeEntry)
            .where(TimeEntry.timesheet_period_id == period_id)
            .order_by(TimeEntry.date_from)
        )
        return list(result.scalars().all())

    async def get_by_id(self, entry_id: uuid.UUID) -> TimeEntry | None:
        return await self.db.get(TimeEntry, entry_id)

    async def _assert_period_open(self, period: TimesheetPeriod) -> None:
        if period.status == PeriodStatus.CLOSED:
            raise HTTPException(status_code=403, detail="Период закрыт, изменения невозможны")

    async def _get_type(self, type_id: uuid.UUID) -> EntryTypeRef:
        t = await self.db.get(EntryTypeRef, type_id)
        if t is None:
            raise HTTPException(status_code=400, detail="Тип трудозатрат не найден")
        return t

    async def _get_type_by_code(self, code: str) -> EntryTypeRef:
        result = await self.db.execute(
            select(EntryTypeRef).where(EntryTypeRef.code == code)
        )
        t = result.scalar_one_or_none()
        if t is None:
            raise HTTPException(status_code=500, detail=f"Тип '{code}' отсутствует в справочнике")
        return t

    async def _validate_assignment(
        self, employee_id: uuid.UUID, assignment_id: uuid.UUID
    ) -> Assignment:
        assignment = await self.db.get(Assignment, assignment_id)
        if not assignment or assignment.employee_id != employee_id:
            raise HTTPException(status_code=404, detail="Назначение не найдено")
        return assignment

    async def _daily_work_hours(
        self, employee_id: uuid.UUID, day: date, exclude_entry_id: uuid.UUID | None = None
    ) -> float:
        work_type = await self._get_type_by_code(WORK)
        q = select(TimeEntry).where(
            TimeEntry.employee_id == employee_id,
            TimeEntry.date_from <= day,
            TimeEntry.date_to >= day,
            TimeEntry.type_id == work_type.id,
        )
        if exclude_entry_id:
            q = q.where(TimeEntry.id != exclude_entry_id)
        result = await self.db.execute(q)
        return float(sum(e.spend_time for e in result.scalars().all()))

    async def create(
        self,
        period: TimesheetPeriod,
        data: TimeEntryCreate,
        producer=None,
    ) -> tuple[TimeEntry, TimeEntry | None]:
        await self._assert_period_open(period)

        entry_type = await self._get_type(data.type_id)

        if entry_type.code not in (SICK_LEAVE, VACATION) and data.assignment_id is None:
            raise HTTPException(
                status_code=400,
                detail="assignment_id обязателен для данного типа трудозатрат",
            )

        if data.assignment_id:
            await self._validate_assignment(period.employee_id, data.assignment_id)

        spend_time = float(data.spend_time) if data.spend_time is not None else None
        overtime_entry: TimeEntry | None = None

        # WORK: проверяем дневной лимит (только однодневные записи)
        if entry_type.code == WORK and data.date_from == data.date_to:
            day_limit = await self.calendar_svc.get_day_limit(data.date_from)
            existing_hours = await self._daily_work_hours(period.employee_id, data.date_from)

            if day_limit == 0.0:
                # Выходной/праздник — всё идёт как переработка
                overtime_type = await self._get_type_by_code(OVERTIME)
                entry = TimeEntry(
                    timesheet_period_id=period.id,
                    employee_id=period.employee_id,
                    assignment_id=data.assignment_id,
                    type_id=overtime_type.id,
                    date_from=data.date_from,
                    date_to=data.date_to,
                    spend_time=spend_time,
                    task_name=data.task_name,
                    task_num=data.task_num,
                    comment=data.comment,
                )
                self.db.add(entry)
                await self.db.flush()
                await self._create_overtime_approval(entry)
                return entry, None

            total_after = existing_hours + (spend_time or 0)
            if total_after > day_limit:
                normal_hours = max(0.0, day_limit - existing_hours)
                overtime_hours = total_after - day_limit
                overtime_type = await self._get_type_by_code(OVERTIME)

                if normal_hours > 0:
                    entry = TimeEntry(
                        timesheet_period_id=period.id,
                        employee_id=period.employee_id,
                        assignment_id=data.assignment_id,
                        type_id=entry_type.id,
                        date_from=data.date_from,
                        date_to=data.date_to,
                        spend_time=normal_hours,
                        task_name=data.task_name,
                        task_num=data.task_num,
                        comment=data.comment,
                    )
                    self.db.add(entry)
                    await self.db.flush()
                else:
                    entry = None

                overtime_entry = TimeEntry(
                    timesheet_period_id=period.id,
                    employee_id=period.employee_id,
                    assignment_id=data.assignment_id,
                    type_id=overtime_type.id,
                    date_from=data.date_from,
                    date_to=data.date_to,
                    spend_time=overtime_hours,
                    task_name=data.task_name,
                    task_num=data.task_num,
                    comment=data.comment,
                )
                self.db.add(overtime_entry)
                await self.db.flush()
                await self._create_overtime_approval(overtime_entry)

                if producer:
                    from src.kafka.events import publish_overtime_created
                    await publish_overtime_created(producer, overtime_entry, period.employee_id)

                return entry or overtime_entry, overtime_entry

        # OVERTIME введён явно
        if entry_type.code == OVERTIME:
            entry = TimeEntry(
                timesheet_period_id=period.id,
                employee_id=period.employee_id,
                assignment_id=data.assignment_id,
                type_id=entry_type.id,
                date_from=data.date_from,
                date_to=data.date_to,
                spend_time=spend_time,
                task_name=data.task_name,
                task_num=data.task_num,
                comment=data.comment,
            )
            self.db.add(entry)
            await self.db.flush()
            await self._create_overtime_approval(entry)
            if producer:
                from src.kafka.events import publish_overtime_created
                await publish_overtime_created(producer, entry, period.employee_id)
            return entry, None

        # SICK_LEAVE / VACATION — spend_time авторасчёт по дням
        if entry_type.code in (SICK_LEAVE, VACATION):
            days = (data.date_to - data.date_from).days + 1
            spend_time = float(days * STANDARD_HOURS)

        entry = TimeEntry(
            timesheet_period_id=period.id,
            employee_id=period.employee_id,
            assignment_id=data.assignment_id,
            type_id=entry_type.id,
            date_from=data.date_from,
            date_to=data.date_to,
            spend_time=spend_time,
            task_name=data.task_name,
            task_num=data.task_num,
            comment=data.comment,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry, None

    async def update(self, entry: TimeEntry, data: TimeEntryUpdate) -> TimeEntry:
        period = await self.db.get(TimesheetPeriod, entry.timesheet_period_id)
        await self._assert_period_open(period)

        if data.spend_time is not None:
            entry.spend_time = data.spend_time
        if data.task_name is not None:
            entry.task_name = data.task_name
        if data.task_num is not None:
            entry.task_num = data.task_num
        if data.comment is not None:
            entry.comment = data.comment
        entry.updated_at = datetime.utcnow()
        await self.db.flush()
        return entry

    async def delete(self, entry: TimeEntry) -> None:
        period = await self.db.get(TimesheetPeriod, entry.timesheet_period_id)
        await self._assert_period_open(period)
        self.db.delete(entry)
        await self.db.flush()

    async def _create_overtime_approval(self, entry: TimeEntry) -> OvertimeApproval:
        approval = OvertimeApproval(
            time_entry_id=entry.id,
            status=ApprovalStatus.PENDING,
        )
        self.db.add(approval)
        await self.db.flush()
        return approval
