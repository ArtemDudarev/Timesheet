from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_async_session
from ..schemas.status import StatusRead, StatusCreate
from ..services import status_service

router = APIRouter(prefix="/statuses", tags=["Statuses"])

@router.get("/", response_model=list[StatusRead])
async def read_statuses(session: AsyncSession = Depends(get_async_session)):
    return await status_service.get_all_statuses(session)

@router.post("/", response_model=StatusRead)
async def add_status(
    status_data: StatusCreate, 
    session: AsyncSession = Depends(get_async_session)
):
    return await status_service.create_status(session, status_data)