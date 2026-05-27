import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user
from src.kafka.events import publish_employee_updated
from src.schemas.employee import EmployeeRead, EmployeeUpdate
from src.services.employee_service import EmployeeService


router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    _: dict = Depends(get_current_user),
):
    service = EmployeeService(session)
    employee = await service.get_employee_full_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    return employee


@router.patch("/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    employee_id: uuid.UUID,
    employee_in: EmployeeUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    is_own = current_user["sub"] == str(employee_id)
    is_manager = "Менеджер" in current_user.get("roles", [])
    if not is_own and not is_manager:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    service = EmployeeService(session)
    employee = await service.get_employee_full_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    employee = await service.update_employee_profile(employee, employee_in)
    await publish_employee_updated(request.app.state.kafka_producer, employee)
    return employee
