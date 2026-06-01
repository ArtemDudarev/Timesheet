from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..dependencies import require_roles
from ..kafka.events import (
    publish_project_role_created,
    publish_project_role_deleted,
    publish_project_role_updated,
)
from ..schemas.project_role import ProjectRoleCreate, ProjectRoleResponse, ProjectRoleUpdate
from ..services.project_role import ProjectRoleService


router = APIRouter(prefix="/project-roles", tags=["Project Roles"])

_manager = Depends(require_roles("Менеджер"))


@router.post("/", response_model=ProjectRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: ProjectRoleCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = ProjectRoleService(session)
    role = await service.create(role_data)
    await publish_project_role_created(request.app.state.kafka_producer, role)
    return role


@router.get("/", response_model=list[ProjectRoleResponse])
async def get_roles(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = ProjectRoleService(session)
    return await service.get_all(skip=skip, limit=limit)


@router.get("/{role_id}", response_model=ProjectRoleResponse)
async def get_role(
    role_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = ProjectRoleService(session)
    role = await service.get_by_id(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Проектная роль не найдена")
    return role


@router.patch("/{role_id}", response_model=ProjectRoleResponse)
async def update_role(
    role_id: UUID,
    role_data: ProjectRoleUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = ProjectRoleService(session)
    role = await service.update(role_id, role_data)
    if not role:
        raise HTTPException(status_code=404, detail="Проектная роль не найдена")
    await publish_project_role_updated(request.app.state.kafka_producer, role)
    return role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = ProjectRoleService(session)
    deleted = await service.delete(role_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Проектная роль не найдена")
    await publish_project_role_deleted(request.app.state.kafka_producer, role_id)
