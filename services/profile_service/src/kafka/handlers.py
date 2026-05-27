import logging
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.models.employee import Employee
from src.models.employee_project import AssignmentStatus, EmployeeProject
from src.models.project import Project
from src.models.project_role import ProjectRole
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
        for field in ("email", "first_name", "last_name", "phone", "address", "image_url"):
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
        result = await session.execute(select(Employee).where(Employee.id == employee_id))
        employee = result.scalar_one_or_none()
        if employee is None:
            logger.warning("employee.role_assigned: employee %s not found", employee_id)
            return
        employee.roles = [await _upsert_role(session, r) for r in roles_data]
        await session.commit()


async def handle_employee_status_changed(payload: dict[str, Any]) -> None:
    employee_id = UUID(str(payload["employee_id"]))
    status_data = payload.get("status") or {}
    async with async_session_maker() as session:
        status = await _upsert_status(session, status_data)
        result = await session.execute(select(Employee).where(Employee.id == employee_id))
        employee = result.scalar_one_or_none()
        if employee is None:
            logger.warning("employee.status_changed: employee %s not found", employee_id)
            return
        employee.status_id = status.id
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
    assignment_status = AssignmentStatus(payload["status"])

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

        existing = await session.get(EmployeeProject, assignment_id)
        if existing is None:
            assignment = EmployeeProject(
                id=assignment_id,
                employee_id=employee_id,
                project_id=project_id,
                project_role_id=project_role.id,
                start_date=date.fromisoformat(start_date_raw) if start_date_raw else None,
                end_date=date.fromisoformat(end_date_raw) if end_date_raw else None,
                status=assignment_status,
            )
            session.add(assignment)
        else:
            existing.project_role_id = project_role.id
            existing.status = assignment_status

        await session.commit()


async def _upsert_employee(session: AsyncSession, employee_data: dict[str, Any]) -> None:
    employee_id = UUID(str(employee_data["id"]))
    roles = [await _upsert_role(session, r) for r in employee_data.get("roles", [])]
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


async def _upsert_project(session: AsyncSession, project_data: dict[str, Any]) -> Project:
    project_id = UUID(str(project_data["id"]))
    start_raw = project_data.get("start_date")
    end_raw = project_data.get("end_date")
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        project = Project(
            id=project_id,
            name=project_data["name"],
            status=project_data["status"],
            start_date=date.fromisoformat(start_raw) if start_raw else None,
            end_date=date.fromisoformat(end_raw) if end_raw else None,
        )
        session.add(project)
        await session.flush()
    else:
        project.name = project_data["name"]
        project.status = project_data["status"]
        project.start_date = date.fromisoformat(start_raw) if start_raw else None
        project.end_date = date.fromisoformat(end_raw) if end_raw else None
    return project


async def _upsert_status(session: AsyncSession, status_data: dict[str, Any]) -> Status:
    status_id = UUID(str(status_data["id"]))
    result = await session.execute(select(Status).where(Status.id == status_id))
    status = result.scalar_one_or_none()
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
    result = await session.execute(select(ProjectRole).where(ProjectRole.id == role_id))
    role = result.scalar_one_or_none()
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
