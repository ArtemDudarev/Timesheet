import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.employee import Employee


async def assert_can_read_employee_data(
    current_user: dict,
    employee_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    perms = set(current_user.get("permissions", []))

    # read_any / timesheet:read_any → проверяется выше через require_permission или здесь
    if "timesheet:read_any" in perms:
        return
    if current_user["sub"] == str(employee_id):
        return
    if "timesheet:read_team" in perms:
        emp = await db.get(Employee, employee_id)
        if emp and emp.lead_id and str(emp.lead_id) == current_user["sub"]:
            return
    raise HTTPException(status_code=403, detail="Недостаточно прав")


async def assert_can_write_employee_data(
    current_user: dict,
    employee_id: uuid.UUID,
) -> None:
    perms = set(current_user.get("permissions", []))
    if "timesheet:edit_any" in perms:
        return
    if current_user["sub"] == str(employee_id):
        return
    raise HTTPException(status_code=403, detail="Недостаточно прав")


async def assert_can_read_summary(
    current_user: dict,
    employee_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    perms = set(current_user.get("permissions", []))

    if "summary:read_any" in perms:
        return
    if current_user["sub"] == str(employee_id):
        return
    if "summary:read_team" in perms:
        emp = await db.get(Employee, employee_id)
        if emp and emp.lead_id and str(emp.lead_id) == current_user["sub"]:
            return
    raise HTTPException(status_code=403, detail="Недостаточно прав")


