import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user
from src.schemas.skill import SkillRead, SkillsUpdate
from src.services.employee_service import EmployeeService
from src.services.skill_service import SkillService

router = APIRouter(tags=["Skills"])


@router.get("/skills", response_model=list[SkillRead])
async def list_skills(
    session: AsyncSession = Depends(get_async_session),
    _: dict = Depends(get_current_user),
):
    return await SkillService(session).get_all()


@router.put("/employees/{employee_id}/skills", status_code=204)
async def update_employee_skills(
    employee_id: uuid.UUID,
    data: SkillsUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    perms = set(current_user.get("permissions", []))
    is_own = current_user["sub"] == str(employee_id)
    can_edit_any = "employee:skills_edit_any" in perms

    if not is_own and not can_edit_any:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    employee = await EmployeeService(session).get_employee_full_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    await SkillService(session).update_employee_skills(employee_id, data.skill_ids)
