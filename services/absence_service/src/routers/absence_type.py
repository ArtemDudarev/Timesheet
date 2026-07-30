from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user
from src.schemas.absence import AbsenceTypeRead
from src.services.absence_service import AbsenceService

router = APIRouter(prefix="/absence-types", tags=["Absence Types"])


@router.get("/", response_model=list[AbsenceTypeRead])
async def get_absence_types(
    session: AsyncSession = Depends(get_async_session),
    _: dict = Depends(get_current_user),
):
    return await AbsenceService(session).get_types()
