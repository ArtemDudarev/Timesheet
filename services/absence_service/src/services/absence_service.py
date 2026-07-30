import uuid
from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import extract, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.absence import Absence, AbsenceStatus
from src.models.absence_type import AbsenceType
from src.models.employee import Employee
from src.schemas.absence import AbsenceCreate, AbsenceUpdate, VacationBalance

ENTITLED_VACATION_DAYS = 28


def count_working_days(date_from: date, date_to: date) -> int:
    """Рабочие дни пн-пт. Праздники не учитываются — производственный календарь
    живёт в timesheet_service (открытый вопрос №9 контракта)."""
    days = 0
    current = date_from
    while current <= date_to:
        if current.weekday() < 5:
            days += 1
        current += timedelta(days=1)
    return days


class AbsenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        employee_id: uuid.UUID | None = None,
        lead_id: uuid.UUID | None = None,
        status: AbsenceStatus | None = None,
        type_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Absence]:
        q = select(Absence)
        if employee_id:
            q = q.where(Absence.employee_id == employee_id)
        elif lead_id:
            # Тимлид видит свои заявки + заявки своей команды
            q = (
                q.join(Employee, Employee.id == Absence.employee_id)
                .where(or_(Employee.lead_id == lead_id, Employee.id == lead_id))
            )
        if status:
            q = q.where(Absence.status == status)
        if type_id:
            q = q.where(Absence.type_id == type_id)
        q = q.order_by(Absence.date_from.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, absence_id: uuid.UUID) -> Absence | None:
        return await self.db.get(Absence, absence_id)

    async def create(self, employee_id: uuid.UUID, data: AbsenceCreate) -> Absence:
        await self._validate_type(data.type_id)
        days = count_working_days(data.date_from, data.date_to)
        if days == 0:
            raise HTTPException(status_code=400, detail="Диапазон не содержит рабочих дней")

        absence = Absence(
            employee_id=employee_id,
            type_id=data.type_id,
            date_from=data.date_from,
            date_to=data.date_to,
            days_count=days,
            comment=data.comment,
            status=AbsenceStatus.PENDING if data.submit else AbsenceStatus.DRAFT,
            submitted_at=datetime.utcnow() if data.submit else None,
        )
        self.db.add(absence)
        await self.db.flush()
        await self.db.refresh(absence, attribute_names=["absence_type"])
        return absence

    async def update(self, absence: Absence, data: AbsenceUpdate) -> Absence:
        if absence.status not in (AbsenceStatus.DRAFT, AbsenceStatus.REJECTED):
            raise HTTPException(
                status_code=409, detail="Изменять можно только черновик или отклонённую заявку"
            )
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(absence, field, value)
        if absence.date_to < absence.date_from:
            raise HTTPException(status_code=422, detail="date_to не может быть раньше date_from")
        absence.days_count = count_working_days(absence.date_from, absence.date_to)
        if absence.days_count == 0:
            raise HTTPException(status_code=400, detail="Диапазон не содержит рабочих дней")
        await self.db.flush()
        return absence

    async def withdraw(self, absence: Absence) -> Absence | None:
        """Отзыв заявки: черновик удаляется, PENDING переводится в «Отменена»."""
        if absence.status == AbsenceStatus.DRAFT:
            await self.db.delete(absence)
            await self.db.flush()
            return None
        if absence.status == AbsenceStatus.PENDING:
            absence.status = AbsenceStatus.CANCELLED
            await self.db.flush()
            return absence
        raise HTTPException(
            status_code=409, detail="Отозвать можно только черновик или заявку на согласовании"
        )

    async def submit(self, absence: Absence) -> Absence:
        if absence.status not in (AbsenceStatus.DRAFT, AbsenceStatus.REJECTED):
            raise HTTPException(status_code=409, detail="Заявка уже отправлена или обработана")
        absence.status = AbsenceStatus.PENDING
        absence.submitted_at = datetime.utcnow()
        absence.approver_id = None
        absence.approved_at = None
        absence.rejection_comment = None
        await self.db.flush()
        return absence

    async def approve(self, absence: Absence, approver_id: uuid.UUID) -> Absence:
        if absence.status != AbsenceStatus.PENDING:
            raise HTTPException(status_code=409, detail="Заявка не находится на согласовании")
        absence.status = AbsenceStatus.APPROVED
        absence.approver_id = approver_id
        absence.approved_at = datetime.utcnow()
        await self.db.flush()
        return absence

    async def reject(self, absence: Absence, approver_id: uuid.UUID, comment: str) -> Absence:
        if absence.status != AbsenceStatus.PENDING:
            raise HTTPException(status_code=409, detail="Заявка не находится на согласовании")
        absence.status = AbsenceStatus.REJECTED
        absence.approver_id = approver_id
        absence.approved_at = datetime.utcnow()
        absence.rejection_comment = comment
        await self.db.flush()
        return absence

    async def vacation_balance(self, employee_id: uuid.UUID, year: int) -> VacationBalance:
        vacation_type = await self._get_type_by_code("VACATION")
        result = await self.db.execute(
            select(Absence).where(
                Absence.employee_id == employee_id,
                Absence.type_id == vacation_type.id,
                Absence.status.in_((AbsenceStatus.APPROVED, AbsenceStatus.PENDING)),
                extract("year", Absence.date_from) == year,
            )
        )
        used = 0
        pending = 0
        for absence in result.scalars().all():
            if absence.status == AbsenceStatus.APPROVED:
                used += absence.days_count
            else:
                pending += absence.days_count
        return VacationBalance(
            year=year,
            entitled_days=ENTITLED_VACATION_DAYS,
            used_days=used,
            pending_days=pending,
            remaining_days=ENTITLED_VACATION_DAYS - used - pending,
        )

    async def get_types(self) -> list[AbsenceType]:
        result = await self.db.execute(select(AbsenceType).order_by(AbsenceType.name))
        return list(result.scalars().all())

    async def _validate_type(self, type_id: uuid.UUID) -> AbsenceType:
        t = await self.db.get(AbsenceType, type_id)
        if t is None:
            raise HTTPException(status_code=400, detail="Тип отсутствия не найден")
        return t

    async def _get_type_by_code(self, code: str) -> AbsenceType:
        result = await self.db.execute(select(AbsenceType).where(AbsenceType.code == code))
        t = result.scalar_one_or_none()
        if t is None:
            raise HTTPException(status_code=500, detail=f"Тип '{code}' отсутствует в справочнике")
        return t
