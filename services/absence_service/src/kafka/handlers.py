import logging
from typing import Any
from uuid import UUID

from src.database import async_session_maker
from src.models.employee import Employee

logger = logging.getLogger(__name__)

# Толерантные упсерты (паттерн reporting_service): порядок событий между
# топиками не гарантирован, отсутствие записи — не ошибка.


async def handle_employee_profile_created(payload: dict[str, Any], producer=None) -> None:
    data = payload.get("employee") or {}
    employee_id = UUID(str(data["id"]))
    async with async_session_maker() as session:
        employee = await session.get(Employee, employee_id)
        if employee is None:
            employee = Employee(
                id=employee_id,
                first_name=data.get("first_name", "Не указано"),
                last_name=data.get("last_name", "Не указано"),
            )
            session.add(employee)
        else:
            employee.first_name = data.get("first_name", employee.first_name)
            employee.last_name = data.get("last_name", employee.last_name)
        await session.commit()


async def handle_employee_updated(payload: dict[str, Any], producer=None) -> None:
    data = payload.get("employee") or {}
    employee_id = UUID(str(data["id"]))
    async with async_session_maker() as session:
        employee = await session.get(Employee, employee_id)
        if employee is None:
            employee = Employee(
                id=employee_id,
                first_name=data.get("first_name", "Не указано"),
                last_name=data.get("last_name", "Не указано"),
            )
            session.add(employee)
        if "lead_id" in data:
            raw = data["lead_id"]
            employee.lead_id = UUID(str(raw)) if raw else None
        await session.commit()
