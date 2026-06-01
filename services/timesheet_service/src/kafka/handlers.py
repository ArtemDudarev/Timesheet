import logging
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.models.employee import Employee
from src.models.employee_project import EmployeeProject
from src.models.project import Project
from src.models.project_role import ProjectRole
from src.models.role import Role
from src.models.user import User
from src.models.user_role import user_role as user_role_table

logger = logging.getLogger(__name__)


async def handle_user_created(payload: dict[str, Any], producer=None) -> None:
    user_data = payload.get("user") or {}
    async with async_session_maker() as session:
        await _upsert_user(session, user_data)
        await session.commit()


async def handle_employee_profile_created(payload: dict[str, Any], producer=None) -> None:
    emp_data = payload.get("employee") or {}
    employee_id = UUID(str(emp_data["id"]))
    async with async_session_maker() as session:
        employee = await session.get(Employee, employee_id)
        if employee is None:
            employee = Employee(
                id=employee_id,
                first_name=emp_data.get("first_name", "Не указано"),
                last_name=emp_data.get("last_name", "Не указано"),
                email=emp_data.get("email"),
                number=emp_data.get("number"),
            )
            session.add(employee)
            await session.flush()

            from src.services.timesheet_period_service import TimesheetPeriodService
            svc = TimesheetPeriodService(session)
            now = datetime.utcnow()
            await svc.create_year_periods(
                employee_id=employee_id,
                year=now.year,
                closed_up_to_month=now.month - 1 if now.month > 1 else None,
            )
        else:
            employee.first_name = emp_data.get("first_name", employee.first_name)
            employee.last_name = emp_data.get("last_name", employee.last_name)
            employee.email = emp_data.get("email", employee.email)
            employee.number = emp_data.get("number", employee.number)
        await session.commit()


async def handle_employee_role_assigned(payload: dict[str, Any], producer=None) -> None:
    employee_id = UUID(str(payload["employee_id"]))
    async with async_session_maker() as session:
        user = await session.get(User, employee_id)
        if user is None:
            return
        roles = [await _upsert_role(session, r) for r in payload.get("roles", [])]
        await _set_user_roles(session, employee_id, roles)
        await session.commit()


async def handle_project_created(payload: dict[str, Any], producer=None) -> None:
    data = payload.get("project") or {}
    await _upsert_project(data)


async def handle_project_updated(payload: dict[str, Any], producer=None) -> None:
    data = payload.get("project") or {}
    await _upsert_project(data)


async def handle_project_deleted(payload: dict[str, Any], producer=None) -> None:
    project_id = UUID(str(payload["project_id"]))
    async with async_session_maker() as session:
        project = await session.get(Project, project_id)
        if project:
            session.delete(project)
            await session.commit()


async def handle_project_role_created(payload: dict[str, Any], producer=None) -> None:
    data = payload.get("project_role") or {}
    await _upsert_project_role(data)


async def handle_project_role_updated(payload: dict[str, Any], producer=None) -> None:
    data = payload.get("project_role") or {}
    await _upsert_project_role(data)


async def handle_project_role_deleted(payload: dict[str, Any], producer=None) -> None:
    role_id = UUID(str(payload["project_role_id"]))
    async with async_session_maker() as session:
        pr = await session.get(ProjectRole, role_id)
        if pr:
            session.delete(pr)
            await session.commit()


async def handle_employee_project_assigned(payload: dict[str, Any], producer=None) -> None:
    async with async_session_maker() as session:
        employee_id = UUID(str(payload["employee_id"]))
        employee = await session.get(Employee, employee_id)
        if employee is None:
            logger.warning("employee.project_assigned: employee %s not found, skipping", employee_id)
            return

        assignment_id = UUID(str(payload["assignment_id"]))
        assignment = await session.get(EmployeeProject, assignment_id)
        if assignment is None:
            assignment = EmployeeProject(
                id=assignment_id,
                employee_id=employee_id,
                project_id=UUID(str(payload["project_id"])),
                project_role_id=UUID(str(payload["project_role"]["id"])),
                status=payload.get("status"),
            )
            raw_start = payload.get("start_date")
            raw_end = payload.get("end_date")
            assignment.start_date = date.fromisoformat(raw_start) if raw_start else None
            assignment.end_date = date.fromisoformat(raw_end) if raw_end else None
            session.add(assignment)
        else:
            assignment.status = payload.get("status", assignment.status)
        await session.commit()


async def handle_role_created(payload: dict[str, Any], producer=None) -> None:
    async with async_session_maker() as session:
        await _upsert_role(session, payload.get("role") or {})
        await session.commit()


async def handle_role_updated(payload: dict[str, Any], producer=None) -> None:
    async with async_session_maker() as session:
        await _upsert_role(session, payload.get("role") or {})
        await session.commit()


async def handle_role_deleted(payload: dict[str, Any], producer=None) -> None:
    role_id = UUID(str(payload["role_id"]))
    async with async_session_maker() as session:
        role = await session.get(Role, role_id)
        if role:
            session.delete(role)
            await session.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

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
        user.is_active = user_data.get("is_active", True)
    return user


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


async def _set_user_roles(session: AsyncSession, user_id: UUID, roles: list[Role]) -> None:
    await session.execute(delete(user_role_table).where(user_role_table.c.user_id == user_id))
    if roles:
        await session.execute(
            insert(user_role_table),
            [{"user_id": user_id, "role_id": r.id} for r in roles],
        )


async def _upsert_project(data: dict[str, Any]) -> None:
    project_id = UUID(str(data["id"]))
    async with async_session_maker() as session:
        project = await session.get(Project, project_id)
        if project is None:
            project = Project(id=project_id, name=data["name"], status=data.get("status"))
            session.add(project)
        else:
            project.name = data["name"]
            project.status = data.get("status")
        await session.commit()


async def _upsert_project_role(data: dict[str, Any]) -> None:
    role_id = UUID(str(data["id"]))
    async with async_session_maker() as session:
        pr = await session.get(ProjectRole, role_id)
        if pr is None:
            pr = ProjectRole(id=role_id, name=data["name"], description=data.get("description"))
            session.add(pr)
        else:
            pr.name = data["name"]
            pr.description = data.get("description")
        await session.commit()
