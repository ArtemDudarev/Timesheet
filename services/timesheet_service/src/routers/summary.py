import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src._access import assert_can_read_summary
from src.database import get_async_session
from src.dependencies import get_current_user
from src.schemas.summary import EmployeeSummaryResponse
from src.services.summary_service import SummaryService

router = APIRouter(tags=["Summary"])


@router.get("/employees/{employee_id}/summary", response_model=EmployeeSummaryResponse)
async def get_employee_summary(
    employee_id: uuid.UUID,
    year: int = date.today().year,
    month: int = date.today().month,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    await assert_can_read_summary(current_user, employee_id, session)

    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="Некорректный месяц")

    return await SummaryService(session).get_summary(employee_id, year, month)
