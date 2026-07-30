import uuid
from datetime import date

import pytest_asyncio

from src.main import app
from src.models.absence import Absence
from src.models.entry_type_ref import EntryTypeRef

from tests.conftest import EMPLOYEE_ID, PERIOD_ID

SICK_TYPE_ID = uuid.UUID("cccccccc-0000-0000-0000-000000000001")


@pytest_asyncio.fixture
async def sick_type(db_session):
    t = EntryTypeRef(id=SICK_TYPE_ID, code="SICK_LEAVE", name="Больничный")
    db_session.add(t)
    await db_session.flush()
    return t


def _published_topics() -> list[str]:
    return [c.args[0] for c in app.state.kafka_producer.publish.call_args_list]


async def _create_sick_entry(client, employee_token) -> str:
    response = await client.post(
        f"/periods/{PERIOD_ID}/entries/",
        json={
            "type_id": str(SICK_TYPE_ID),
            "date_from": "2026-06-10",
            "date_to": "2026-06-11",
        },
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 201
    return response.json()["id"]


async def test_create_entry_publishes_event(client, employee_token, test_period, sick_type):
    await _create_sick_entry(client, employee_token)
    assert "timesheet.entry_created" in _published_topics()


async def test_update_entry_publishes_event(client, employee_token, test_period, sick_type):
    entry_id = await _create_sick_entry(client, employee_token)
    response = await client.patch(
        f"/periods/{PERIOD_ID}/entries/{entry_id}",
        json={"comment": "Справка приложена"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    assert "timesheet.entry_updated" in _published_topics()


async def test_create_entry_blocked_by_approved_absence(
    client, employee_token, test_period, sick_type, db_session
):
    """Интеграция с absence_service: на даты согласованного отсутствия запись не создаётся."""
    db_session.add(Absence(
        id=uuid.uuid4(),
        employee_id=EMPLOYEE_ID,
        type_code="VACATION",
        date_from=date(2026, 6, 8),
        date_to=date(2026, 6, 12),
        status="Согласована",
    ))
    await db_session.flush()

    response = await client.post(
        f"/periods/{PERIOD_ID}/entries/",
        json={
            "type_id": str(SICK_TYPE_ID),
            "date_from": "2026-06-10",
            "date_to": "2026-06-11",
        },
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 400
    assert "отсутствие" in response.json()["detail"]


async def test_delete_entry_really_deletes(client, employee_token, test_period, sick_type):
    """Регрессия: self.db.delete без await — запись молча не удалялась."""
    entry_id = await _create_sick_entry(client, employee_token)

    response = await client.delete(
        f"/periods/{PERIOD_ID}/entries/{entry_id}",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 204

    response = await client.get(
        f"/periods/{PERIOD_ID}/entries/",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.json() == []  # запись реально удалена
    assert "timesheet.entry_deleted" in _published_topics()
