from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_async_session
from src.dependencies import get_current_user
from src.schemas.status import StatusRead
from src.services import status_service

router = APIRouter(prefix="/statuses", tags=["Statuses"])

@router.get("/", response_model=list[StatusRead])
async def read_statuses(
    session: AsyncSession = Depends(get_async_session),
    _: dict = Depends(get_current_user),
):
    return await status_service.get_all_statuses(session)
