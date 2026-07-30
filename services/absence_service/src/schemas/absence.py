import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, model_validator

from src.models.absence import AbsenceStatus


class AbsenceTypeRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    color: str
    requires_approval: bool

    model_config = {"from_attributes": True}


class AbsenceCreate(BaseModel):
    type_id: uuid.UUID
    date_from: date
    date_to: date
    comment: Optional[str] = None
    submit: bool = False

    @model_validator(mode="after")
    def validate_dates(self) -> "AbsenceCreate":
        if self.date_to < self.date_from:
            raise ValueError("date_to не может быть раньше date_from")
        return self


class AbsenceUpdate(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    comment: Optional[str] = None


class AbsenceApprove(BaseModel):
    comment: Optional[str] = None


class AbsenceReject(BaseModel):
    comment: str  # обязателен — осознанно строже overtime-прецедента (см. контракт)


class AbsenceRead(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    absence_type: AbsenceTypeRead
    date_from: date
    date_to: date
    days_count: int
    status: AbsenceStatus
    comment: Optional[str]
    submitted_at: Optional[datetime]
    approver_id: Optional[uuid.UUID]
    approved_at: Optional[datetime]
    rejection_comment: Optional[str]

    model_config = {"from_attributes": True}


class VacationBalance(BaseModel):
    year: int
    entitled_days: int = 28
    used_days: int
    pending_days: int
    remaining_days: int
