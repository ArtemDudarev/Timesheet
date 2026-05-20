import logging
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.models.employee import Employee
from src.models.role import Role
from src.models.status import Status

logger = logging.getLogger(__name__)


async def handle_employee_created(payload: dict[str, Any]) -> None:
    employee_data = payload.get("employee") or {}
    async with async_session_maker() as session:
        await _upsert_employee(session, employee_data)


async def handle_employee_updated(payload: dict[str, Any]) -> None:
    employee_data = payload.get("employee") or {}
    employee_id = UUID(str(employee_data["id"]))
    async with async_session_maker() as session:
        result = await session.execute(select(Employee).where(Employee.id == employee_id))
        employee = result.scalar_one_or_none()
        if employee is None:
            logger.warning("employee.updated: employee %s not found", employee_id)
            return
        for field in ("email", "first_name", "last_name", "phone", "address", "birthday", "image_url"):
            if field in employee_data:
                setattr(employee, field, employee_data[field])
        await session.commit()


async def _upsert_employee(session: AsyncSession, employee_data: dict[str, Any]) -> None:
    employee_id = UUID(str(employee_data["id"]))
    roles = [await _get_or_create_role(session, r) for r in employee_data.get("roles", [])]
    status = await _get_or_create_default_status(session)

    result = await session.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()

    if employee is None:
        employee = Employee(
            id=employee_id,
            first_name="Не указано",
            last_name="Не указано",
            email=employee_data["email"],
            hashed_password=employee_data.get("hashed_password", ""),
            number=employee_data.get("employee_number"),
            register_date=date.today(),
            status_id=status.id,
            roles=roles,
        )
        session.add(employee)
    else:
        employee.email = employee_data["email"]
        employee.hashed_password = employee_data.get("hashed_password", employee.hashed_password)
        employee.number = employee_data.get("employee_number")
        employee.roles = roles

    await session.commit()


async def _get_or_create_role(session: AsyncSession, role_data: dict[str, Any]) -> Role:
    result = await session.execute(select(Role).where(Role.name == role_data["name"]))
    role = result.scalar_one_or_none()
    if role is None:
        role = Role(name=role_data["name"], description=role_data.get("description"))
        session.add(role)
        await session.flush()
    return role


async def _get_or_create_default_status(session: AsyncSession) -> Status:
    result = await session.execute(select(Status).where(Status.name == "Новый"))
    status = result.scalar_one_or_none()
    if status is None:
        status = Status(name="Новый", description="Статус сотрудника после регистрации")
        session.add(status)
        await session.flush()
    return status
