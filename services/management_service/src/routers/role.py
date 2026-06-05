import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import require_permission
from src.kafka.events import publish_role_created, publish_role_deleted, publish_role_updated
from src.schemas.role import RoleCreate, RoleRead, RoleUpdate
from src.services.role_service import RoleService


router = APIRouter(prefix="/roles", tags=["Roles"])

_manager = Depends(require_permission("system:manage"))


@router.post("/", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_in: RoleCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = RoleService(session)
    if await service.get_by_name(role_in.name):
        raise HTTPException(status_code=400, detail="Роль уже существует")
    role = await service.create(role_in)
    await publish_role_created(request.app.state.kafka_producer, role)
    return role


@router.get("/", response_model=list[RoleRead])
async def get_roles(
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = RoleService(session)
    return await service.get_all()


@router.get("/{role_id}", response_model=RoleRead)
async def get_role(
    role_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = RoleService(session)
    role = await service.get_by_id(role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Роль не найдена")
    return role


@router.patch("/{role_id}", response_model=RoleRead)
async def update_role(
    role_id: uuid.UUID,
    role_in: RoleUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = RoleService(session)
    role = await service.get_by_id(role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Роль не найдена")

    if role_in.name and role_in.name != role.name:
        existing_role = await service.get_by_name(role_in.name)
        if existing_role:
            raise HTTPException(status_code=400, detail="Роль уже существует")

    role = await service.update(role, role_in)
    await publish_role_updated(request.app.state.kafka_producer, role)
    return role


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Роль не найдена"},
        400: {"description": "Роль нельзя удалить, так как она назначена сотрудникам"},
    },
)
async def delete_role(
    role_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = RoleService(session)
    role = await service.get_by_id(role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Роль не найдена")
    await service.delete(role)
    await publish_role_deleted(request.app.state.kafka_producer, role_id)
    return {"message": f"Роль '{role.name}' успешно удалена"}
