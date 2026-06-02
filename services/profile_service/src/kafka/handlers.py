import logging
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.models.employee import Employee
from src.models.assignment_status import AssignmentStatus
from src.models.employee_project import Assignment
from src.models.project import Project
from src.models.project_status import ProjectStatus
from src.models.project_role import ProjectRole
from src.models.role import Role
from src.models.status import Status
from src.models.user import User
from src.models.user_role import user_role as user_role_table

logger = logging.getLogger(__name__)


async def handle_user_created(payload: dict[str, Any]) -> None:
    user_data = payload.get("user") or {}
    async with async_session_maker() as session:
        user = await _upsert_user(session, user_data)
        roles = [await _upsert_role(session, r) for r in user_data.get("roles", [])]
        await _set_user_roles(session, user.id, roles)
        await _upsert_employee_profile(session, user.id)
        await session.commit()


async def handle_employee_updated(payload: dict[str, Any]) -> None:
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


async def handle_employee_role_assigned(payload: dict[str, Any]) -> None:
    employee_id = UUID(str(payload["employee_id"]))
    roles_data = payload.get("roles", [])
    async with async_session_maker() as session:
        user = await session.get(User, employee_id)
        if user is None:
            logger.warning("employee.role_assigned: user %s not found", employee_id)
            return
        roles = [await _upsert_role(session, r) for r in roles_data]
        await _set_user_roles(session, user.id, roles)
        await session.commit()


async def handle_employee_status_changed(payload: dict[str, Any]) -> None:
    employee_id = UUID(str(payload["employee_id"]))
    status_data = payload.get("status") or {}
    async with async_session_maker() as session:
        status = await _upsert_status(session, status_data)
        employee = await session.get(Employee, employee_id)
        if employee is None:
            logger.warning("employee.status_changed: employee %s not found", employee_id)
            return
        employee.status_id = status.id
        await session.commit()


async def handle_status_created(payload: dict[str, Any]) -> None:
    async with async_session_maker() as session:
        await _upsert_status(session, payload.get("status") or {})
        await session.commit()


async def handle_status_updated(payload: dict[str, Any]) -> None:
    async with async_session_maker() as session:
        await _upsert_status(session, payload.get("status") or {})
        await session.commit()


async def handle_status_deleted(payload: dict[str, Any]) -> None:
    status_id = UUID(str(payload["status_id"]))
    async with async_session_maker() as session:
        await session.execute(delete(Status).where(Status.id == status_id))
        await session.commit()


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


async def handle_project_created(payload: dict[str, Any]) -> None:
    async with async_session_maker() as session:
        await _upsert_project(session, payload.get("project") or {})
        await session.commit()


async def handle_project_updated(payload: dict[str, Any]) -> None:
    async with async_session_maker() as session:
        await _upsert_project(session, payload.get("project") or {})
        await session.commit()


async def handle_project_deleted(payload: dict[str, Any]) -> None:
    project_id = UUID(str(payload["project_id"]))
    async with async_session_maker() as session:
        await session.execute(delete(Project).where(Project.id == project_id))
        await session.commit()


async def handle_employee_project_assigned(payload: dict[str, Any]) -> None:
    assignment_id = UUID(str(payload["assignment_id"]))
    employee_id = UUID(str(payload["employee_id"]))
    project_id = UUID(str(payload["project_id"]))
    role_data = payload.get("project_role") or {}
    start_date_raw = payload.get("start_date")
    end_date_raw = payload.get("end_date")
    status_id = UUID(str(payload["status_id"]))

    async with async_session_maker() as session:
        employee = await session.get(Employee, employee_id)
        if employee is None:
            logger.warning("employee.project_assigned: employee %s not found", employee_id)
            return

        project = await session.get(Project, project_id)
        if project is None:
            logger.warning("employee.project_assigned: project %s not found", project_id)
            return

        project_role = await _upsert_project_role(session, role_data)

        existing = await session.get(Assignment, assignment_id)
        if existing is None:
            assignment = Assignment(
                id=assignment_id,
                employee_id=employee_id,
                project_id=project_id,
                project_role_id=project_role.id,
                start_date=date.fromisoformat(start_date_raw) if start_date_raw else None,
                end_date=date.fromisoformat(end_date_raw) if end_date_raw else None,
                status_id=status_id,
            )
            session.add(assignment)
        else:
            existing.project_role_id = project_role.id
            existing.status_id = status_id

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


async def _upsert_project(session: AsyncSession, project_data: dict[str, Any]) -> Project:
    project_id = UUID(str(project_data["id"]))
    start_raw = project_data.get("start_date")
    end_raw = project_data.get("end_date")
    status_id = UUID(str(project_data["status_id"]))
    project = await session.get(Project, project_id)
    if project is None:
        project = Project(
            id=project_id,
            name=project_data["name"],
            status_id=status_id,
            start_date=date.fromisoformat(start_raw) if start_raw else None,
            end_date=date.fromisoformat(end_raw) if end_raw else None,
        )
        session.add(project)
        await session.flush()
    else:
        project.name = project_data["name"]
        project.status_id = status_id
        project.start_date = date.fromisoformat(start_raw) if start_raw else None
        project.end_date = date.fromisoformat(end_raw) if end_raw else None
    return project


async def _upsert_status(session: AsyncSession, status_data: dict[str, Any]) -> Status:
    status_id = UUID(str(status_data["id"]))
    status = await session.get(Status, status_id)
    if status is None:
        status = Status(id=status_id, name=status_data["name"], description=status_data.get("description"))
        session.add(status)
        await session.flush()
    else:
        status.name = status_data["name"]
        status.description = status_data.get("description")
    return status


async def _upsert_project_role(session: AsyncSession, role_data: dict[str, Any]) -> ProjectRole:
    role_id = UUID(str(role_data["id"]))
    role = await session.get(ProjectRole, role_id)
    if role is None:
        role = ProjectRole(id=role_id, name=role_data["name"], description=role_data.get("description"))
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
