import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import require_roles
from src.kafka.events import publish_status_created, publish_status_deleted, publish_status_updated
from src.schemas.status import StatusCreate, StatusRead, StatusUpdate
from src.services.status_service import StatusService


router = APIRouter(prefix="/statuses", tags=["Statuses"])

_manager = Depends(require_roles("Менеджер"))


@router.post("/", response_model=StatusRead, status_code=status.HTTP_201_CREATED)
async def add_status(
    status_data: StatusCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = StatusService(session)
    if await service.get_by_name(status_data.name):
        raise HTTPException(status_code=400, detail="Статус уже существует")
    db_status = await service.create(status_data)
    await publish_status_created(request.app.state.kafka_producer, db_status)
    return db_status


@router.get("/", response_model=list[StatusRead])
async def read_statuses(
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = StatusService(session)
    return await service.get_all()


@router.get("/{status_id}", response_model=StatusRead)
async def get_status(
    status_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
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
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = StatusService(session)
    db_status = await service.get_by_id(status_id)
    if not db_status:
        raise HTTPException(status_code=404, detail="Статус не найден")

    if status_data.name and status_data.name != db_status.name:
        existing_status = await service.get_by_name(status_data.name)
        if existing_status:
            raise HTTPException(status_code=400, detail="Статус уже существует")

    db_status = await service.update(db_status, status_data)
    await publish_status_updated(request.app.state.kafka_producer, db_status)
    return db_status


@router.delete(
    "/{status_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Статус не найден"},
        400: {"description": "Статус нельзя удалить, так как он назначен сотрудникам"},
    },
)
async def delete_status(
    status_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = StatusService(session)
    db_status = await service.get_by_id(status_id)
    if not db_status:
        raise HTTPException(status_code=404, detail="Статус не найден")
    await service.delete(db_status)
    await publish_status_deleted(request.app.state.kafka_producer, status_id)
    return {"message": f"Статус '{db_status.name}' успешно удалён"}
