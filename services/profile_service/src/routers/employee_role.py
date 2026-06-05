import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user
from src.schemas.employee_role import EmployeeRoleRead
from src.services.employee_role_service import EmployeeRoleService


router = APIRouter(prefix="/employee-roles", tags=["Employee Roles"])


@router.get("/employee/{employee_id}", response_model=list[EmployeeRoleRead])
async def get_employee_roles_by_employee(
    employee_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    _: dict = Depends(get_current_user),
):
    service = EmployeeRoleService(session)
    return await service.get_by_employee_id(employee_id)



