import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.schemas.status import StatusCreate, StatusRead, StatusUpdate
from src.services.status_service import StatusService


router = APIRouter(prefix="/statuses", tags=["Statuses"])


@router.post("/", response_model=StatusRead, status_code=status.HTTP_201_CREATED)
async def add_status(
    status_data: StatusCreate,
    session: AsyncSession = Depends(get_async_session),
):
    service = StatusService(session)
    if await service.get_by_name(status_data.name):
        raise HTTPException(status_code=400, detail="Статус уже существует")
    return await service.create(status_data)


@router.get("/", response_model=list[StatusRead])
async def read_statuses(session: AsyncSession = Depends(get_async_session)):
    service = StatusService(session)
    return await service.get_all()


@router.get("/{status_id}", response_model=StatusRead)
async def get_status(
    status_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
):
    service = StatusService(session)
    db_status = await service.get_by_id(status_id)
    if not db_status:
        raise HTTPException(status_code=404, detail="Статус не найден")
    return db_status


@router.patch("/{status_id}", response_model=StatusRead)
async def update_status(
    status_id: uuid.UUID,
    status_data: StatusUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    service = StatusService(session)
    db_status = await service.get_by_id(status_id)
    if not db_status:
        raise HTTPException(status_code=404, detail="Статус не найден")

    if status_data.name and status_data.name != db_status.name:
        existing_status = await service.get_by_name(status_data.name)
        if existing_status:
            raise HTTPException(status_code=400, detail="Статус уже существует")

    return await service.update(db_status, status_data)
