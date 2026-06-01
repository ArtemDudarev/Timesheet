from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import require_roles
from src.models.assignment_status import AssignmentStatus
from src.schemas.assignment_status import AssignmentStatusResponse

router = APIRouter(prefix="/assignment-statuses", tags=["Assignment Statuses"])

_manager = Depends(require_roles("Менеджер"))


@router.get("/", response_model=list[AssignmentStatusResponse])
async def get_assignment_statuses(
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    result = await session.execute(select(AssignmentStatus).order_by(AssignmentStatus.name))
    return list(result.scalars().all())
