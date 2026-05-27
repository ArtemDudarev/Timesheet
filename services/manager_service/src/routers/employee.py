import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import require_roles
from src.kafka.events import (
    publish_employee_project_assigned,
    publish_employee_role_assigned,
    publish_employee_status_changed,
)
from src.schemas.assignment import AssignmentCreate, AssignmentRead, AssignmentUpdate
from src.schemas.employee import (
    EmployeeListRead,
    EmployeeRead,
    EmployeeRolesUpdate,
    EmployeeStatusUpdate,
)
from src.services.assignment_service import AssignmentService
from src.services.employee_service import EmployeeService


router = APIRouter(prefix="/employees", tags=["employees"])

_manager = Depends(require_roles("Менеджер"))


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
    _: dict = _manager,
):
    service = EmployeeService(session)
    return await service.get_all_with_related(skip=skip, limit=limit)


@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = EmployeeService(session)
    return await get_employee_or_404(employee_id, service)


@router.patch("/{employee_id}/roles", response_model=EmployeeRead)
async def update_employee_roles(
    employee_id: uuid.UUID,
    payload: EmployeeRolesUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = EmployeeService(session)
    employee = await get_employee_or_404(employee_id, service)
    employee = await service.update_employee_roles(employee, payload.role_ids)
    await publish_employee_role_assigned(request.app.state.kafka_producer, employee.user)
    return employee


@router.patch("/{employee_id}/status", response_model=EmployeeRead)
async def update_employee_status(
    employee_id: uuid.UUID,
    payload: EmployeeStatusUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = EmployeeService(session)
    employee = await get_employee_or_404(employee_id, service)
    employee = await service.update_employee_status(employee, payload.status_id)
    await publish_employee_status_changed(request.app.state.kafka_producer, employee)
    return employee


@router.post("/{employee_id}/assignments", response_model=AssignmentRead, status_code=201)
async def create_assignment(
    employee_id: uuid.UUID,
    payload: AssignmentCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    emp_service = EmployeeService(session)
    await get_employee_or_404(employee_id, emp_service)

    service = AssignmentService(session)
    assignment = await service.create(employee_id, payload)
    await publish_employee_project_assigned(request.app.state.kafka_producer, assignment)
    return assignment


@router.patch("/{employee_id}/assignments/{assignment_id}", response_model=AssignmentRead)
async def update_assignment(
    employee_id: uuid.UUID,
    assignment_id: uuid.UUID,
    payload: AssignmentUpdate,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    emp_service = EmployeeService(session)
    await get_employee_or_404(employee_id, emp_service)

    service = AssignmentService(session)
    assignment = await service.get_by_id(assignment_id, employee_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Назначение не найдено")

    return await service.update(assignment, payload)


@router.delete("/{employee_id}/assignments/{assignment_id}", status_code=204)
async def delete_assignment(
    employee_id: uuid.UUID,
    assignment_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    emp_service = EmployeeService(session)
    await get_employee_or_404(employee_id, emp_service)

    service = AssignmentService(session)
    assignment = await service.get_by_id(assignment_id, employee_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Назначение не найдено")

    await service.delete(assignment)
