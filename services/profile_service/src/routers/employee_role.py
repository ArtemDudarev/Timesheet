import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.schemas.employee_role import EmployeeRoleRead
from src.services.employee_role_service import EmployeeRoleService


router = APIRouter(prefix="/employee-roles", tags=["Employee Roles"])


@router.get("/employee/{employee_id}", response_model=list[EmployeeRoleRead])
async def get_employee_roles_by_employee(
    employee_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
):
    service = EmployeeRoleService(session)
    return await service.get_by_employee_id(employee_id)


@router.get("/role/{role_id}", response_model=list[EmployeeRoleRead])
async def get_employee_roles_by_role(
    role_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
):
    service = EmployeeRoleService(session)
    return await service.get_by_role_id(role_id)


@router.get("/{employee_role_id}", response_model=EmployeeRoleRead)
async def get_employee_role(
    employee_role_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
):
    service = EmployeeRoleService(session)
    employee_role = await service.get_by_id(employee_role_id)

    if employee_role is None:
        raise HTTPException(status_code=404, detail="Employee role not found")

    return employee_role
