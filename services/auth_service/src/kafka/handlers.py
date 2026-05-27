import logging
from typing import Any
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.models.role import Role
from src.models.user import User
from src.models.user_role import user_role as user_role_table

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


async def handle_user_role_assigned(payload: dict[str, Any]) -> None:
    user_id = UUID(str(payload["employee_id"]))
    roles_data = payload.get("roles", [])
    async with async_session_maker() as session:
        user = await session.get(User, user_id)
        if user is None:
            logger.warning("employee.role_assigned: user %s not found", user_id)
            return
        roles = [await _upsert_role(session, r) for r in roles_data]
        await _set_user_roles(session, user.id, roles)
        await session.commit()


async def _set_user_roles(session: AsyncSession, user_id: UUID, roles: list[Role]) -> None:
    await session.execute(delete(user_role_table).where(user_role_table.c.user_id == user_id))
    if roles:
        await session.execute(
            insert(user_role_table),
            [{"user_id": user_id, "role_id": role.id} for role in roles],
        )


async def _upsert_role(session: AsyncSession, role_data: dict[str, Any]) -> Role:
    role_id = UUID(str(role_data["id"]))
    role = await session.get(Role, role_id)
    if role is not None:
        role.name = role_data["name"]
        role.description = role_data.get("description")
        return role
    # Проверяем по имени — могла быть засеяна с другим UUID
    result = await session.execute(select(Role).where(Role.name == role_data["name"]))
    role = result.scalar_one_or_none()
    if role is not None:
        role.description = role_data.get("description")
        return role
    role = Role(id=role_id, name=role_data["name"], description=role_data.get("description"))
    session.add(role)
    await session.flush()
    return role
