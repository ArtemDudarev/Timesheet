from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_async_session
from src.schemas.project import ProjectRead
from src.services.project_service import ProjectService

router = APIRouter(prefix="/project", tags=["Project"])

@router.get("/", response_model=list[ProjectRead])
async def get_all_projects(session: AsyncSession = Depends(get_async_session)):
    service = ProjectService(session)
    return await service.get_all_projects()

@router.get("/{project_id}", response_model=ProjectRead)
async def get_project_by_id(project_id: UUID, session: AsyncSession = Depends(get_async_session)):
    service = ProjectService(session)
    project = await service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return project
