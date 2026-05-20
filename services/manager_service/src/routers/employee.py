import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.kafka.events import (
    publish_employee_project_assigned,
    publish_employee_role_assigned,
    publish_employee_status_changed,
)
from src.schemas.employee import (
    EmployeeListRead,
    EmployeeProjectRolesUpdate,
    EmployeeProjectsUpdate,
    EmployeeRead,
    EmployeeRolesUpdate,
    EmployeeStatusUpdate,
)
from src.services.employee_service import EmployeeService


router = APIRouter(prefix="/employees", tags=["employees"])


async def get_employee_or_404(
    employee_id: uuid.UUID,
    service: EmployeeService,
):
    employee = await service.get_employee_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    return employee


@router.get("/", response_model=list[EmployeeListRead])
async def get_employees(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
):
    service = EmployeeService(session)
    return await service.get_all_with_related(skip=skip, limit=limit)


@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
):
    service = EmployeeService(session)
    return await get_employee_or_404(employee_id, service)


@router.patch("/{employee_id}/roles", response_model=EmployeeRead)
async def update_employee_roles(
    employee_id: uuid.UUID,
    payload: EmployeeRolesUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    service = EmployeeService(session)
    employee = await get_employee_or_404(employee_id, service)
    employee = await service.update_employee_roles(employee, payload.role_ids)
    await publish_employee_role_assigned(request.app.state.kafka_producer, employee)
    return employee


@router.patch("/{employee_id}/projects", response_model=EmployeeRead)
async def update_employee_projects(
    employee_id: uuid.UUID,
    payload: EmployeeProjectsUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    service = EmployeeService(session)
    employee = await get_employee_or_404(employee_id, service)
    employee = await service.update_employee_projects(employee, payload.project_ids)
    for project in employee.projects:
        await publish_employee_project_assigned(
            request.app.state.kafka_producer,
            employee.id,
            project.id,
        )
    return employee


@router.patch("/{employee_id}/project-roles", response_model=EmployeeRead)
async def update_employee_project_roles(
    employee_id: uuid.UUID,
    payload: EmployeeProjectRolesUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    service = EmployeeService(session)
    employee = await get_employee_or_404(employee_id, service)
    return await service.update_employee_project_roles(employee, payload.project_role_ids)


@router.patch("/{employee_id}/status", response_model=EmployeeRead)
async def update_employee_status(
    employee_id: uuid.UUID,
    payload: EmployeeStatusUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    service = EmployeeService(session)
    employee = await get_employee_or_404(employee_id, service)
    employee = await service.update_employee_status(employee, payload.status_id)
    await publish_employee_status_changed(request.app.state.kafka_producer, employee)
    return employee
