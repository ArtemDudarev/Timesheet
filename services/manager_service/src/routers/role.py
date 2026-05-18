import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.schemas.role import RoleCreate, RoleRead, RoleUpdate
from src.services.role_service import RoleService


router = APIRouter(prefix="/role", tags=["Roles"])


@router.post("/", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_in: RoleCreate,
    session: AsyncSession = Depends(get_async_session),
):
    service = RoleService(session)
    if await service.get_by_name(role_in.name):
        raise HTTPException(status_code=400, detail="Роль уже существует")
    return await service.create(role_in)


@router.get("/", response_model=list[RoleRead])
async def get_roles(
    session: AsyncSession = Depends(get_async_session),
):
    service = RoleService(session)
    return await service.get_all()


@router.get("/{role_id}", response_model=RoleRead)
async def get_role(
    role_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
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
    session: AsyncSession = Depends(get_async_session),
):
    service = RoleService(session)
    role = await service.get_by_id(role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Роль не найдена")

    if role_in.name and role_in.name != role.name:
        existing_role = await service.get_by_name(role_in.name)
        if existing_role:
            raise HTTPException(status_code=400, detail="Роль уже существует")

    return await service.update(role, role_in)
