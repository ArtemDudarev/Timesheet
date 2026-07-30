import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.employee import Employee
from src.models.notification import Notification, NotificationType
from src.models.notification_preference import DEFAULT_TYPE_TOGGLES, NotificationPreference
from src.models.role import Role
from src.models.user import User
from src.models.user_role import user_role as user_role_table
from src.schemas.notification import NotificationPreferenceUpdate


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        user_id: uuid.UUID,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Notification]:
        q = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            q = q.where(Notification.is_read.is_(False))
        q = q.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def mark_read(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Notification:
        notification = await self.db.get(Notification, notification_id)
        # Чужое уведомление неотличимо от несуществующего
        if notification is None or notification.user_id != user_id:
            raise HTTPException(status_code=404, detail="Уведомление не найдено")
        notification.is_read = True
        await self.db.flush()
        return notification

    async def mark_all_read(self, user_id: uuid.UUID) -> None:
        await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        await self.db.flush()

    async def get_preferences(self, user_id: uuid.UUID) -> NotificationPreference:
        prefs = await self.db.get(NotificationPreference, user_id)
        if prefs is None:
            # Дефолты без записи в БД — запись появится при первом PATCH
            prefs = NotificationPreference(
                user_id=user_id,
                email_enabled=True,
                push_enabled=True,
                type_toggles=dict(DEFAULT_TYPE_TOGGLES),
            )
        return prefs

    async def update_preferences(
        self, user_id: uuid.UUID, data: NotificationPreferenceUpdate
    ) -> NotificationPreference:
        prefs = await self.db.get(NotificationPreference, user_id)
        if prefs is None:
            prefs = NotificationPreference(
                user_id=user_id,
                email_enabled=True,
                push_enabled=True,
                type_toggles=dict(DEFAULT_TYPE_TOGGLES),
            )
            self.db.add(prefs)
        update_data = data.model_dump(exclude_unset=True)
        if "type_toggles" in update_data:
            # Частичное обновление: неупомянутые ключи сохраняются
            merged = dict(prefs.type_toggles)
            merged.update(update_data.pop("type_toggles"))
            prefs.type_toggles = merged
        for field, value in update_data.items():
            setattr(prefs, field, value)
        await self.db.flush()
        return prefs

    # ── Создание уведомлений из Kafka-событий ─────────────────────────────────

    async def notify(
        self,
        user_ids: list[uuid.UUID],
        type_: NotificationType,
        title: str,
        text: str,
        target_url: str | None = None,
    ) -> list[Notification]:
        """Создаёт уведомления, пропуская получателей с выключенным toggle этого типа."""
        created: list[Notification] = []
        for user_id in dict.fromkeys(user_ids):  # dedup с сохранением порядка
            if not await self._type_enabled(user_id, type_):
                continue
            notification = Notification(
                user_id=user_id,
                type=type_,
                title=title,
                text=text,
                target_url=target_url,
                created_at=datetime.utcnow(),
            )
            self.db.add(notification)
            created.append(notification)
        await self.db.flush()
        return created

    async def resolve_approvers(self, employee_id: uuid.UUID) -> list[uuid.UUID]:
        """Кому слать «ждёт согласования»: лид сотрудника, а если лида нет — все Менеджеры."""
        employee = await self.db.get(Employee, employee_id)
        if employee is not None and employee.lead_id is not None:
            return [employee.lead_id]
        return await self.get_user_ids_with_roles("Менеджер")

    async def get_user_ids_with_roles(self, *role_names: str) -> list[uuid.UUID]:
        result = await self.db.execute(
            select(user_role_table.c.user_id)
            .join(Role, Role.id == user_role_table.c.role_id)
            .join(User, User.id == user_role_table.c.user_id)
            .where(Role.name.in_(role_names), User.is_active.is_(True))
            .distinct()
        )
        return list(result.scalars().all())

    async def get_employee_name(self, employee_id: uuid.UUID) -> str:
        employee = await self.db.get(Employee, employee_id)
        if employee is None:
            return "Сотрудник"
        return f"{employee.first_name} {employee.last_name}"

    async def _type_enabled(self, user_id: uuid.UUID, type_: NotificationType) -> bool:
        prefs = await self.db.get(NotificationPreference, user_id)
        if prefs is None:
            return True
        # Отсутствующий в toggles ключ считается включённым
        return bool(prefs.type_toggles.get(type_.value, True))
