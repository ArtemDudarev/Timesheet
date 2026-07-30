import logging
from datetime import date
from typing import Any
from uuid import UUID

from src.database import async_session_maker
from src.models.department import Department
from src.models.employee import Employee
from src.models.project import Project
from src.models.time_entry_replica import TimeEntryReplica

logger = logging.getLogger(__name__)

# Все хендлеры — толерантные упсерты: события между топиками приходят в
# произвольном порядке (при холодном реплее — особенно), поэтому отсутствие
# записи никогда не ошибка, а повторная доставка ничего не ломает.


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
            # profile_created мог ещё не дойти — создаём с плейсхолдерами
            employee = Employee(
                id=employee_id,
                first_name=data.get("first_name", "Не указано"),
                last_name=data.get("last_name", "Не указано"),
            )
            session.add(employee)
        else:
            if data.get("first_name"):
                employee.first_name = data["first_name"]
            if data.get("last_name"):
                employee.last_name = data["last_name"]
        if "department_id" in data:
            raw = data["department_id"]
            employee.department_id = UUID(str(raw)) if raw else None
        await session.commit()


async def handle_department_upsert(payload: dict[str, Any], producer=None) -> None:
    data = payload.get("department") or {}
    department_id = UUID(str(data["id"]))
    async with async_session_maker() as session:
        department = await session.get(Department, department_id)
        if department is None:
            session.add(Department(id=department_id, name=data.get("name", "Не указано")))
        else:
            department.name = data.get("name", department.name)
        await session.commit()


async def handle_department_deleted(payload: dict[str, Any], producer=None) -> None:
    department_id = UUID(str(payload["department_id"]))
    async with async_session_maker() as session:
        department = await session.get(Department, department_id)
        if department:
            await session.delete(department)
            await session.commit()


async def handle_project_upsert(payload: dict[str, Any], producer=None) -> None:
    data = payload.get("project") or {}
    project_id = UUID(str(data["id"]))
    async with async_session_maker() as session:
        project = await session.get(Project, project_id)
        if project is None:
            project = Project(id=project_id, name=data.get("name", "Не указано"))
            session.add(project)
        else:
            project.name = data.get("name", project.name)
        # Старые события (до A.3) этих полей не несут — .get оставит None
        project.client = data.get("client")
        project.status = data.get("status")
        project.budget_hours = data.get("budget_hours")
        deadline_raw = data.get("deadline")
        project.deadline = date.fromisoformat(deadline_raw) if deadline_raw else None
        await session.commit()


async def handle_project_deleted(payload: dict[str, Any], producer=None) -> None:
    project_id = UUID(str(payload["project_id"]))
    async with async_session_maker() as session:
        project = await session.get(Project, project_id)
        if project:
            await session.delete(project)
            await session.commit()


async def handle_entry_upsert(payload: dict[str, Any], producer=None) -> None:
    entry_id = UUID(str(payload["entry_id"]))
    async with async_session_maker() as session:
        entry = await session.get(TimeEntryReplica, entry_id)
        if entry is None:
            entry = TimeEntryReplica(entry_id=entry_id)
            session.add(entry)
        entry.period_id = UUID(str(payload["period_id"]))
        entry.employee_id = UUID(str(payload["employee_id"]))
        entry.project_id = UUID(str(payload["project_id"])) if payload.get("project_id") else None
        entry.type_code = payload.get("type_code")
        entry.date_from = date.fromisoformat(payload["date_from"])
        entry.date_to = date.fromisoformat(payload["date_to"])
        entry.spend_time = payload.get("spend_time")
        entry.year = payload["year"]
        entry.month = payload["month"]
        await session.commit()


async def handle_entry_deleted(payload: dict[str, Any], producer=None) -> None:
    entry_id = UUID(str(payload["entry_id"]))
    async with async_session_maker() as session:
        entry = await session.get(TimeEntryReplica, entry_id)
        if entry:
            await session.delete(entry)
            await session.commit()
