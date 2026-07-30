"""Юнит-тесты логики выбора получателей и создания уведомлений (уровень сервиса)."""
from src.models.notification import NotificationType
from src.services.notification_service import NotificationService

from tests.conftest import EMPLOYEE_ID, MANAGER_ID, TEAMLEAD_ID


async def test_resolve_approvers_lead(db_session, test_employee, manager_user):
    svc = NotificationService(db_session)
    recipients = await svc.resolve_approvers(EMPLOYEE_ID)
    assert recipients == [TEAMLEAD_ID]  # есть лид — менеджеров не трогаем


async def test_resolve_approvers_fallback_to_managers(
    db_session, test_employee_without_lead, manager_user
):
    svc = NotificationService(db_session)
    recipients = await svc.resolve_approvers(EMPLOYEE_ID)
    assert recipients == [MANAGER_ID]


async def test_notify_respects_toggles(client, db_session, employee_token):
    # Выключаем APPROVAL через API, затем notify не должен создать уведомление
    await client.patch(
        "/notifications/preferences",
        json={"type_toggles": {"APPROVAL": False}},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    svc = NotificationService(db_session)
    created = await svc.notify(
        [EMPLOYEE_ID], NotificationType.APPROVAL, "Заголовок", "Текст"
    )
    assert created == []

    # Другой тип не выключен — уведомление создаётся
    created = await svc.notify(
        [EMPLOYEE_ID], NotificationType.PASSWORD, "Заголовок", "Текст"
    )
    assert len(created) == 1


async def test_notify_dedups_recipients(db_session):
    svc = NotificationService(db_session)
    created = await svc.notify(
        [EMPLOYEE_ID, EMPLOYEE_ID], NotificationType.APPROVAL, "Заголовок", "Текст"
    )
    assert len(created) == 1


async def test_get_employee_name_fallback(db_session):
    svc = NotificationService(db_session)
    assert await svc.get_employee_name(EMPLOYEE_ID) == "Сотрудник"
