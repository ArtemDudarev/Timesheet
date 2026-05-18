from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..schemas.project_role import ProjectRoleCreate, ProjectRoleResponse, ProjectRoleUpdate
from ..services.project_role import ProjectRoleService


router = APIRouter(prefix="/project-roles", tags=["Project Roles"])


@router.post("/", response_model=ProjectRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: ProjectRoleCreate,
    session: AsyncSession = Depends(get_async_session),
):
    service = ProjectRoleService(session)
    return await service.create(role_data)


@router.get("/", response_model=list[ProjectRoleResponse])
async def get_roles(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
):
    service = ProjectRoleService(session)
    return await service.get_all(skip=skip, limit=limit)


@router.get("/{role_id}", response_model=ProjectRoleResponse)
async def get_role(
    role_id: UUID,
    session: AsyncSession = Depends(get_async_session),
):
    service = ProjectRoleService(session)
    role = await service.get_by_id(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Project role not found")
    return role


@router.patch("/{role_id}", response_model=ProjectRoleResponse)
async def update_role(
    role_id: UUID,
    role_data: ProjectRoleUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    service = ProjectRoleService(session)
    role = await service.update(role_id, role_data)
    if not role:
        raise HTTPException(status_code=404, detail="Project role not found")
    return role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    session: AsyncSession = Depends(get_async_session),
):
    service = ProjectRoleService(session)
    deleted = await service.delete(role_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project role not found")
