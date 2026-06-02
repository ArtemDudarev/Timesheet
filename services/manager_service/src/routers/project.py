from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import require_roles
from src.kafka.events import publish_project_created, publish_project_deleted, publish_project_updated
from src.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from src.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])

_manager = Depends(require_roles("Менеджер"))


@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = ProjectService(session)
    existing_project = await service.get_by_name(payload.name)
    if existing_project:
        raise HTTPException(status_code=400, detail="Проект уже существует")
    project = await service.create_project(payload)
    await publish_project_created(request.app.state.kafka_producer, project)
    return project


@router.get("/", response_model=list[ProjectRead])
async def get_all_projects(
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = ProjectService(session)
    return await service.get_all_projects()


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project_by_id(
    project_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = ProjectService(session)
    project = await service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = ProjectService(session)
    project = await service.update_project(project_id, payload)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    await publish_project_updated(request.app.state.kafka_producer, project)
    return project


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Проект не найден"},
        400: {"description": "Проект нельзя удалить, так как он используется в назначениях"},
    },
)
async def delete_project(
    project_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = ProjectService(session)
    deleted = await service.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Проект не найден")
    await publish_project_deleted(request.app.state.kafka_producer, project_id)
    return {"message": "Project deleted successfully"}
