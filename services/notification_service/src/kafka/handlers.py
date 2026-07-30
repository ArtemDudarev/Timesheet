import logging
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.models.employee import Employee
from src.models.notification import NotificationType
from src.models.role import Role
from src.models.user import User
from src.models.user_role import user_role as user_role_table
from src.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


# ── Реплики (паттерн timesheet_service) ───────────────────────────────────────

async def handle_user_created(payload: dict[str, Any], producer=None) -> None:
    user_data = payload.get("user") or {}
    async with async_session_maker() as session:
        user = await _upsert_user(session, user_data)
        roles = [await _upsert_role(session, r) for r in user_data.get("roles", [])]
        await _set_user_roles(session, user.id, roles)
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
        else:
            employee.first_name = emp_data.get("first_name", employee.first_name)
            employee.last_name = emp_data.get("last_name", employee.last_name)
            employee.email = emp_data.get("email", employee.email)
            employee.number = emp_data.get("number", employee.number)
        await session.commit()


async def handle_employee_updated(payload: dict[str, Any], producer=None) -> None:
    employee_data = payload.get("employee") or {}
    employee_id = UUID(str(employee_data["id"]))
    async with async_session_maker() as session:
        employee = await session.get(Employee, employee_id)
        if employee is None:
            logger.warning("employee.updated: employee %s not found", employee_id)
            return
        if "lead_id" in employee_data:
            raw = employee_data["lead_id"]
            employee.lead_id = UUID(raw) if raw else None
        await session.commit()


async def handle_employee_role_assigned(payload: dict[str, Any], producer=None) -> None:
    employee_id = UUID(str(payload["employee_id"]))
    async with async_session_maker() as session:
        user = await session.get(User, employee_id)
        if user is None:
            raise RuntimeError(
                f"employee.role_assigned: user {employee_id} not found — "
                "event will be retried on next restart"
            )
        roles = [await _upsert_role(session, r) for r in payload.get("roles", [])]
        await _set_user_roles(session, employee_id, roles)
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
            await session.delete(role)
            await session.commit()


# ── События → уведомления ─────────────────────────────────────────────────────

async def handle_period_submitted(payload: dict[str, Any], producer=None) -> None:
    employee_id = UUID(str(payload["employee_id"]))
    async with async_session_maker() as session:
        svc = NotificationService(session)
        recipients = await svc.resolve_approvers(employee_id)
        name = await svc.get_employee_name(employee_id)
        await svc.notify(
            recipients,
            NotificationType.APPROVAL,
            "Табель на согласовании",
            f"{name} отправил(а) табель за {payload['month']:02d}.{payload['year']}",
        )
        await session.commit()


async def handle_period_approved(payload: dict[str, Any], producer=None) -> None:
    employee_id = UUID(str(payload["employee_id"]))
    async with async_session_maker() as session:
        svc = NotificationService(session)
        await svc.notify(
            [employee_id],
            NotificationType.APPROVAL,
            "Табель согласован",
            f"Ваш табель за {payload['month']:02d}.{payload['year']} согласован",
        )
        await session.commit()


async def handle_period_rejected(payload: dict[str, Any], producer=None) -> None:
    employee_id = UUID(str(payload["employee_id"]))
    comment = payload.get("comment")
    text = f"Ваш табель за {payload['month']:02d}.{payload['year']} отклонён"
    if comment:
        text += f": {comment}"
    async with async_session_maker() as session:
        svc = NotificationService(session)
        await svc.notify([employee_id], NotificationType.APPROVAL, "Табель отклонён", text)
        await session.commit()


async def handle_overtime_created(payload: dict[str, Any], producer=None) -> None:
    employee_id = UUID(str(payload["employee_id"]))
    async with async_session_maker() as session:
        svc = NotificationService(session)
        recipients = await svc.resolve_approvers(employee_id)
        name = await svc.get_employee_name(employee_id)
        date_from = date.fromisoformat(payload["date_from"])
        await svc.notify(
            recipients,
            NotificationType.APPROVAL,
            "Переработка на согласовании",
            f"{name}: переработка {payload['spend_time']} ч от {date_from.strftime('%d.%m.%Y')}",
        )
        await session.commit()


ABSENCE_TYPE_NAMES = {
    "VACATION": "отпуск",
    "SICK": "больничный",
    "TRIP": "командировку",
    "DAY_OFF": "отгул",
}

# Значения AbsenceStatus из absence_service (payload absence.status_changed)
ABSENCE_PENDING = "На согласовании"
ABSENCE_APPROVED = "Согласована"
ABSENCE_REJECTED = "Отклонена"


async def handle_absence_status_changed(payload: dict[str, Any], producer=None) -> None:
    employee_id = UUID(str(payload["employee_id"]))
    status = payload["status"]
    type_name = ABSENCE_TYPE_NAMES.get(payload.get("type_code"), "отсутствие")
    dates = f"{payload['date_from']} — {payload['date_to']}"

    async with async_session_maker() as session:
        svc = NotificationService(session)
        if status == ABSENCE_PENDING:
            recipients = await svc.resolve_approvers(employee_id)
            name = await svc.get_employee_name(employee_id)
            await svc.notify(
                recipients,
                NotificationType.APPROVAL,
                "Заявка на отсутствие",
                f"{name} просит согласовать {type_name}: {dates}",
            )
        elif status == ABSENCE_APPROVED:
            await svc.notify(
                [employee_id],
                NotificationType.APPROVAL,
                "Отсутствие согласовано",
                f"Ваша заявка на {type_name} ({dates}) согласована",
            )
        elif status == ABSENCE_REJECTED:
            await svc.notify(
                [employee_id],
                NotificationType.APPROVAL,
                "Отсутствие отклонено",
                f"Ваша заявка на {type_name} ({dates}) отклонена",
            )
        await session.commit()


# Значения DocumentStatus из document_service (payload document.route_updated)
DOCUMENT_SIGNED = "Подписан"
DOCUMENT_REJECTED = "Отклонён"


async def handle_document_route_updated(payload: dict[str, Any], producer=None) -> None:
    status = payload["status"]
    title = payload.get("title", "Документ")
    author_id = UUID(str(payload["author_id"]))
    current_raw = payload.get("current_step_employee_id")

    async with async_session_maker() as session:
        svc = NotificationService(session)
        if status == DOCUMENT_SIGNED:
            await svc.notify(
                [author_id], NotificationType.DOC,
                "Документ подписан", f"«{title}» прошёл весь маршрут подписания",
            )
        elif status == DOCUMENT_REJECTED:
            await svc.notify(
                [author_id], NotificationType.DOC,
                "Документ отклонён", f"«{title}» отклонён участником маршрута",
            )
        elif current_raw:
            await svc.notify(
                [UUID(str(current_raw))], NotificationType.DOC,
                "Документ ждёт подписи", f"«{title}» ожидает вашего действия",
            )
        await session.commit()


async def handle_password_reset_requested(payload: dict[str, Any], producer=None) -> None:
    async with async_session_maker() as session:
        svc = NotificationService(session)
        recipients = await svc.get_user_ids_with_roles("Менеджер", "Администратор")
        await svc.notify(
            recipients,
            NotificationType.PASSWORD,
            "Заявка на сброс пароля",
            f"Поступила заявка на сброс пароля: {payload['identifier']}",
        )
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
