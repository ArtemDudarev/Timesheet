import logging
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.kafka.events import publish_employee_profile_created
from src.models.employee import Employee
from src.models.role import Role
from src.models.status import Status
from src.models.user import User
from src.models.user_role import user_role as user_role_table

logger = logging.getLogger(__name__)


async def handle_user_created(payload: dict[str, Any], producer=None) -> None:
    user_data = payload.get("user") or {}
    async with async_session_maker() as session:
        user = await _upsert_user(session, user_data)
        roles = [await _upsert_role(session, r) for r in user_data.get("roles", [])]
        await _set_user_roles(session, user.id, roles)
        employee = await _upsert_employee_profile(session, user.id)
        await session.commit()
    if producer:
        await publish_employee_profile_created(producer, employee, user)


async def handle_employee_updated(payload: dict[str, Any], producer=None) -> None:
    employee_data = payload.get("employee") or {}
    employee_id = UUID(str(employee_data["id"]))
    async with async_session_maker() as session:
        employee = await session.get(Employee, employee_id)
        if employee is None:
            logger.warning("employee.updated: employee %s not found", employee_id)
            return
        for field in ("first_name", "last_name", "phone", "address", "image_url"):
            if field in employee_data:
                setattr(employee, field, employee_data[field])
        if "birthday" in employee_data:
            raw = employee_data["birthday"]
            employee.birthday = date.fromisoformat(raw) if raw else None
        await session.commit()


async def _upsert_user(session: AsyncSession, user_data: dict[str, Any]) -> User:
    user_id = UUID(str(user_data["id"]))
    register_date_raw = user_data.get("register_date")
    user = await session.get(User, user_id)
    if user is None:
        user = User(
            id=user_id,
            email=user_data["email"],
            number=user_data.get("number"),
            is_active=user_data.get("is_active", True),
            register_date=date.fromisoformat(register_date_raw) if register_date_raw else date.today(),
        )
        session.add(user)
        await session.flush()
    else:
        user.email = user_data["email"]
        user.number = user_data.get("number")
        user.is_active = user_data.get("is_active", True)
    return user


async def _upsert_employee_profile(session: AsyncSession, user_id: UUID) -> Employee:
    employee = await session.get(Employee, user_id)
    if employee is None:
        status = await _get_or_create_default_status(session)
        employee = Employee(
            id=user_id,
            first_name="Не указано",
            last_name="Не указано",
            status_id=status.id,
        )
        session.add(employee)
        await session.flush()
    return employee


async def _upsert_role(session: AsyncSession, role_data: dict[str, Any]) -> Role:
    role_id = UUID(str(role_data["id"]))
    role = await session.get(Role, role_id)
    if role is None:
        role = Role(id=role_id, name=role_data["name"], description=role_data.get("description"))
        session.add(role)
        await session.flush()
    else:
        role.name = role_data["name"]
        role.description = role_data.get("description")
    return role


async def _get_or_create_default_status(session: AsyncSession) -> Status:
    result = await session.execute(select(Status).where(Status.name == "Новый"))
    status = result.scalar_one_or_none()
    if status is None:
        status = Status(name="Новый", description="Статус сотрудника после регистрации")
        session.add(status)
        await session.flush()
    return status


async def _set_user_roles(session: AsyncSession, user_id: UUID, roles: list[Role]) -> None:
    await session.execute(delete(user_role_table).where(user_role_table.c.user_id == user_id))
    if roles:
        await session.execute(
            insert(user_role_table),
            [{"user_id": user_id, "role_id": role.id} for role in roles],
        )
