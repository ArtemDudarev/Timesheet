import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user
from src.routers.absence import _assert_can_read
from src.schemas.absence import VacationBalance
from src.services.absence_service import AbsenceService

router = APIRouter(prefix="/employees", tags=["Vacation Balance"])


@router.get("/{employee_id}/vacation-balance", response_model=VacationBalance)
async def vacation_balance(
    employee_id: uuid.UUID,
    year: int | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    await _assert_can_read(current_user, employee_id, session)
    return await AbsenceService(session).vacation_balance(
        employee_id, year or date.today().year
    )
