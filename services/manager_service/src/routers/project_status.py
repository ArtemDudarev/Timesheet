from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import require_roles
from src.models.project_status import ProjectStatus
from src.schemas.project_status import ProjectStatusResponse

router = APIRouter(prefix="/project-statuses", tags=["Project Statuses"])

_manager = Depends(require_roles("Менеджер"))


@router.get("/", response_model=list[ProjectStatusResponse])
async def get_project_statuses(
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    result = await session.execute(select(ProjectStatus).order_by(ProjectStatus.name))
    return list(result.scalars().all())
