import uuid

import pytest_asyncio

from src.models.employee_project import Assignment
from src.models.entry_type_ref import EntryTypeRef
from src.models.project import Project
from src.models.project_role import ProjectRole
from tests.conftest import EMPLOYEE_ID, PERIOD_ID

WORK_TYPE_ID = uuid.UUID("dddddddd-0000-0000-0000-000000000001")
OVERTIME_TYPE_ID = uuid.UUID("dddddddd-0000-0000-0000-000000000002")
ASSIGNMENT_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000001")


@pytest_asyncio.fixture
async def work_assignment(db_session, test_employee):
    role = ProjectRole(id=uuid.uuid4(), name="Разработчик")
    project = Project(id=uuid.uuid4(), name="Проект")
    db_session.add_all([role, project])
    await db_session.flush()
    assignment = Assignment(
        id=ASSIGNMENT_ID, employee_id=EMPLOYEE_ID, project_id=project.id,
        project_role_id=role.id, status="ACTIVE",
    )
    db_session.add(assignment)
    db_session.add_all([
        EntryTypeRef(id=WORK_TYPE_ID, code="WORK", name="Работа"),
        EntryTypeRef(id=OVERTIME_TYPE_ID, code="OVERTIME", name="Переработка"),
    ])
    await db_session.flush()
    # Свежесозданный в сессии объект не проходит SELECT — lazy="selectin" для
    # project/project_role не срабатывает без явного refresh (см. test_summary.py)
    await db_session.refresh(assignment, attribute_names=["project", "project_role"])
    return assignment


async def _create(client, employee_token, spend_time, date_="2026-06-10"):
    return await client.post(
        f"/periods/{PERIOD_ID}/entries/",
        json={
            "type_id": str(WORK_TYPE_ID),
            "assignment_id": str(ASSIGNMENT_ID),
            "date_from": date_, "date_to": date_,
            "spend_time": spend_time,
        },
        headers={"Authorization": f"Bearer {employee_token}"},
    )


async def test_daily_total_over_24h_rejected(client, employee_token, test_period, work_assignment):
    """20ч (8 нормы + 12 переработки) уже списано — попытка добавить ещё 10 (итого 30) должна отклоняться."""
    resp1 = await _create(client, employee_token, 20)
    assert resp1.status_code == 201

    resp2 = await _create(client, employee_token, 10)
    assert resp2.status_code == 400
    assert "24" in resp2.json()["detail"]


async def test_daily_total_exactly_24h_allowed(client, employee_token, test_period, work_assignment):
    """Ровно 24ч суммарно за день — граничное значение, должно проходить."""
    resp1 = await _create(client, employee_token, 20)
    assert resp1.status_code == 201

    resp2 = await _create(client, employee_token, 4)
    assert resp2.status_code == 201
