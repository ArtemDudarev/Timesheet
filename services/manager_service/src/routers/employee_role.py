import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.kafka.events import publish_employee_role_assigned
from src.models.employee import Employee
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


async def _publish_roles_for_employee(
    request: Request,
    session: AsyncSession,
    employee_id: uuid.UUID,
) -> None:
    result = await session.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()
    if employee:
        await publish_employee_role_assigned(request.app.state.kafka_producer, employee)


@router.post("/employee/{employee_id}", response_model=list[EmployeeRoleRead])
async def add_employee_roles(
    employee_id: uuid.UUID,
    payload: EmployeeRolesUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    service = EmployeeRoleService(session)
    await validate_employee_roles(service, employee_id, payload.role_ids)
    result = await service.add_roles_to_employee(employee_id, payload.role_ids)
    await _publish_roles_for_employee(request, session, employee_id)
    return result


@router.patch("/employee/{employee_id}", response_model=list[EmployeeRoleRead])
async def update_employee_roles(
    employee_id: uuid.UUID,
    payload: EmployeeRolesUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    service = EmployeeRoleService(session)
    await validate_employee_roles(service, employee_id, payload.role_ids)
    result = await service.replace_employee_roles(employee_id, payload.role_ids)
    await _publish_roles_for_employee(request, session, employee_id)
    return result


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
