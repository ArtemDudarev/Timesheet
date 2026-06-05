import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user
from src.kafka.events import publish_employee_updated
from src.models.employee import Employee
from src.schemas.employee import EmployeeRead, EmployeeUpdate
from src.services.employee_service import EmployeeService


router = APIRouter(prefix="/employees", tags=["employees"])


def _check_read_access(current_user: dict, employee: Employee) -> None:
    perms = set(current_user.get("permissions", []))
    if "employee:read_any" in perms:
        return
    if current_user["sub"] == str(employee.id):
        return
    if "employee:read_team" in perms:
        if employee.lead_id and str(employee.lead_id) == current_user["sub"]:
            return
    raise HTTPException(status_code=403, detail="Недостаточно прав")


@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    service = EmployeeService(session)
    employee = await service.get_employee_full_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    _check_read_access(current_user, employee)
    return employee


@router.patch("/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    employee_id: uuid.UUID,
    employee_in: EmployeeUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    perms = set(current_user.get("permissions", []))
    is_own = current_user["sub"] == str(employee_id)
    can_edit_any = "employee:edit_any" in perms
    can_assign_grade = "employee:assign_grade" in perms

    if not is_own and not can_edit_any and not can_assign_grade:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    if not is_own and not can_edit_any:
        # HR (employee:assign_grade): может изменять только grade_id и department_id
        data = employee_in.model_dump(exclude_unset=True)
        extra = set(data) - {"grade_id", "department_id"}
        if extra:
            raise HTTPException(
                status_code=403,
                detail="HR может изменять только грейд и отдел сотрудника",
            )
        if not data:
            raise HTTPException(status_code=400, detail="Не указаны поля для обновления")
        employee_in = EmployeeUpdate.model_validate(data)
    elif is_own and not can_edit_any:
        # Сотрудник/Тимлид: нельзя менять grade/dept
        data = employee_in.model_dump(exclude_unset=True, exclude={"department_id", "grade_id"})
        employee_in = EmployeeUpdate.model_validate(data)

    service = EmployeeService(session)
    employee = await service.get_employee_full_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    employee = await service.update_employee_profile(employee, employee_in)
    await publish_employee_updated(request.app.state.kafka_producer, employee)
    return employee
