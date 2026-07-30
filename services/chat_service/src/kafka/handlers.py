import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select

from src.database import async_session_maker
from src.models.channel import Channel, ChannelMember, ChannelType
from src.models.employee import Employee
from src.models.project import Project

logger = logging.getLogger(__name__)

# Толерантные упсерты — порядок событий между топиками не гарантирован.


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


async def handle_project_upsert(payload: dict[str, Any], producer=None) -> None:
    """Реплика проекта + автосоздание группового канала проекта."""
    data = payload.get("project") or {}
    project_id = UUID(str(data["id"]))
    name = data.get("name", "Проект")
    async with async_session_maker() as session:
        project = await session.get(Project, project_id)
        if project is None:
            session.add(Project(id=project_id, name=name))
        else:
            project.name = name

        result = await session.execute(
            select(Channel).where(Channel.project_id == project_id)
        )
        channel = result.scalar_one_or_none()
        if channel is None:
            session.add(Channel(type=ChannelType.GROUP, name=name, project_id=project_id))
        else:
            channel.name = name
        await session.commit()


async def handle_project_deleted(payload: dict[str, Any], producer=None) -> None:
    project_id = UUID(str(payload["project_id"]))
    async with async_session_maker() as session:
        result = await session.execute(
            select(Channel).where(Channel.project_id == project_id)
        )
        channel = result.scalar_one_or_none()
        if channel:
            await session.delete(channel)
        project = await session.get(Project, project_id)
        if project:
            await session.delete(project)
        await session.commit()


async def handle_employee_project_assigned(payload: dict[str, Any], producer=None) -> None:
    """Назначение на проект → членство в канале проекта."""
    employee_id = UUID(str(payload["employee_id"]))
    project_id = UUID(str(payload["project_id"]))
    async with async_session_maker() as session:
        result = await session.execute(
            select(Channel).where(Channel.project_id == project_id)
        )
        channel = result.scalar_one_or_none()
        if channel is None:
            # project.created мог ещё не дойти — создаём канал сразу
            project = await session.get(Project, project_id)
            channel = Channel(
                type=ChannelType.GROUP,
                name=project.name if project else "Проект",
                project_id=project_id,
            )
            session.add(channel)
            await session.flush()

        member = await session.get(ChannelMember, (channel.id, employee_id))
        if member is None:
            session.add(ChannelMember(channel_id=channel.id, employee_id=employee_id))
        await session.commit()
