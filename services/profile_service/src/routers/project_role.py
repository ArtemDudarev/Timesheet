from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..schemas.project_role import ProjectRoleResponse
from ..services.project_role import ProjectRoleService


router = APIRouter(prefix="/project-roles", tags=["Project Roles"])


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
        raise HTTPException(status_code=404, detail="Проектная роль не найдена")
    return role
