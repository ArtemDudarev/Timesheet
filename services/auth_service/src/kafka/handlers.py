import logging
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.models.employee import Employee
from src.models.role import Role

logger = logging.getLogger(__name__)


async def handle_role_created(payload: dict[str, Any]) -> None:
    async with async_session_maker() as session:
        await _upsert_role(session, payload.get("role") or {})
        await session.commit()


async def handle_role_updated(payload: dict[str, Any]) -> None:
    async with async_session_maker() as session:
        await _upsert_role(session, payload.get("role") or {})
        await session.commit()


async def handle_role_deleted(payload: dict[str, Any]) -> None:
    role_id = UUID(str(payload["role_id"]))
    async with async_session_maker() as session:
        await session.execute(delete(Role).where(Role.id == role_id))
        await session.commit()


async def handle_employee_role_assigned(payload: dict[str, Any]) -> None:
    employee_id = UUID(str(payload["employee_id"]))
    roles_data = payload.get("roles", [])
    async with async_session_maker() as session:
        result = await session.execute(select(Employee).where(Employee.id == employee_id))
        employee = result.scalar_one_or_none()
        if employee is None:
            logger.warning("employee.role_assigned: employee %s not found", employee_id)
            return
        employee.roles = [await _upsert_role(session, r) for r in roles_data]
        await session.commit()


async def handle_employee_updated(payload: dict[str, Any]) -> None:
    employee_data = payload.get("employee") or {}
    employee_id = UUID(str(employee_data["id"]))
    async with async_session_maker() as session:
        result = await session.execute(select(Employee).where(Employee.id == employee_id))
        employee = result.scalar_one_or_none()
        if employee is None:
            logger.warning("employee.updated: employee %s not found", employee_id)
            return
        if "email" in employee_data:
            employee.email = employee_data["email"]
        await session.commit()


async def _upsert_role(session: AsyncSession, role_data: dict[str, Any]) -> Role:
    role_id = UUID(str(role_data["id"]))
    result = await session.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if role is None:
        role = Role(id=role_id, name=role_data["name"], description=role_data.get("description"))
        session.add(role)
        await session.flush()
    else:
        role.name = role_data["name"]
        role.description = role_data.get("description")
    return role
