import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.schemas.employee_role import EmployeeRoleRead, EmployeeRolesUpdate
from src.services.employee_role_service import EmployeeRoleService


router = APIRouter(prefix="/employee-roles", tags=["Employee Roles"])


async def validate_employee_roles(
    service: EmployeeRoleService,
    employee_id: uuid.UUID,
    role_ids: list[uuid.UUID],
) -> None:
    if not await service.employee_exists(employee_id):
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    existing_role_ids = await service.get_existing_role_ids(role_ids)
    missing_role_ids = set(role_ids) - existing_role_ids
    if missing_role_ids:
        raise HTTPException(status_code=404, detail="Одна или несколько ролей не найдены")


@router.post("/employee/{employee_id}", response_model=list[EmployeeRoleRead])
async def add_employee_roles(
    employee_id: uuid.UUID,
    payload: EmployeeRolesUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    service = EmployeeRoleService(session)
    await validate_employee_roles(service, employee_id, payload.role_ids)
    return await service.add_roles_to_employee(employee_id, payload.role_ids)


@router.patch("/employee/{employee_id}", response_model=list[EmployeeRoleRead])
async def update_employee_roles(
    employee_id: uuid.UUID,
    payload: EmployeeRolesUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    service = EmployeeRoleService(session)
    await validate_employee_roles(service, employee_id, payload.role_ids)
    return await service.replace_employee_roles(employee_id, payload.role_ids)


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
