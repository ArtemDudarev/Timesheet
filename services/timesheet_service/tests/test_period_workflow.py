from tests.conftest import PERIOD_ID, OUTSIDER_PERIOD_ID

from src.models.timesheet_period import PeriodStatus, SubmissionStatus


# ── Submit ────────────────────────────────────────────────────────────────────

async def test_submit_own_period(client, employee_token, test_period):
    response = await client.post(
        f"/periods/{PERIOD_ID}/submit",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["submission_status"] == "На согласовании"
    assert body["submitted_at"] is not None


async def test_submit_foreign_period_forbidden(client, employee_token, test_outsider_period):
    response = await client.post(
        f"/periods/{OUTSIDER_PERIOD_ID}/submit",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


async def test_submit_twice_conflict(client, employee_token, test_period):
    headers = {"Authorization": f"Bearer {employee_token}"}
    await client.post(f"/periods/{PERIOD_ID}/submit", headers=headers)
    response = await client.post(f"/periods/{PERIOD_ID}/submit", headers=headers)
    assert response.status_code == 409


async def test_submit_closed_period_conflict(client, employee_token, test_period, db_session):
    test_period.status = PeriodStatus.CLOSED
    await db_session.flush()
    response = await client.post(
        f"/periods/{PERIOD_ID}/submit",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 409


# ── Approve ───────────────────────────────────────────────────────────────────

async def test_approve_by_manager(client, employee_token, manager_token, test_period):
    await client.post(
        f"/periods/{PERIOD_ID}/submit",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    response = await client.post(
        f"/periods/{PERIOD_ID}/approve",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["submission_status"] == "Согласован"
    assert body["approved_by"] is not None
    assert body["approved_at"] is not None


async def test_approve_by_teamlead_own_team(client, employee_token, teamlead_token, test_period):
    await client.post(
        f"/periods/{PERIOD_ID}/submit",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    response = await client.post(
        f"/periods/{PERIOD_ID}/approve",
        headers={"Authorization": f"Bearer {teamlead_token}"},
    )
    assert response.status_code == 200
    assert response.json()["submission_status"] == "Согласован"


async def test_approve_by_teamlead_foreign_team(client, teamlead_token, test_outsider_period):
    response = await client.post(
        f"/periods/{OUTSIDER_PERIOD_ID}/approve",
        headers={"Authorization": f"Bearer {teamlead_token}"},
    )
    assert response.status_code == 403


async def test_approve_by_employee_forbidden(client, employee_token, test_period):
    response = await client.post(
        f"/periods/{PERIOD_ID}/approve",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


async def test_approve_not_pending_conflict(client, manager_token, test_period):
    response = await client.post(
        f"/periods/{PERIOD_ID}/approve",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 409


# ── Reject ────────────────────────────────────────────────────────────────────

async def test_reject_requires_comment(client, employee_token, manager_token, test_period):
    await client.post(
        f"/periods/{PERIOD_ID}/submit",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    response = await client.post(
        f"/periods/{PERIOD_ID}/reject",
        json={},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 422


async def test_reject_with_comment(client, employee_token, manager_token, test_period):
    await client.post(
        f"/periods/{PERIOD_ID}/submit",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    response = await client.post(
        f"/periods/{PERIOD_ID}/reject",
        json={"comment": "Не заполнены часы за 15-е число"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["submission_status"] == "Отклонён"
    assert body["rejection_comment"] == "Не заполнены часы за 15-е число"


async def test_resubmit_after_reject(client, employee_token, manager_token, test_period):
    emp_headers = {"Authorization": f"Bearer {employee_token}"}
    mgr_headers = {"Authorization": f"Bearer {manager_token}"}
    await client.post(f"/periods/{PERIOD_ID}/submit", headers=emp_headers)
    await client.post(
        f"/periods/{PERIOD_ID}/reject",
        json={"comment": "Исправить"},
        headers=mgr_headers,
    )
    response = await client.post(f"/periods/{PERIOD_ID}/submit", headers=emp_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["submission_status"] == "На согласовании"
    assert body["rejection_comment"] is None


# ── Close: взаимодействие с submission_status ─────────────────────────────────

async def test_close_unapproved_period_conflict(client, manager_token, test_period):
    response = await client.post(
        f"/periods/{PERIOD_ID}/close",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Период не согласован"


async def test_full_workflow_submit_approve_close(
    client, employee_token, manager_token, test_period
):
    emp_headers = {"Authorization": f"Bearer {employee_token}"}
    mgr_headers = {"Authorization": f"Bearer {manager_token}"}

    response = await client.post(f"/periods/{PERIOD_ID}/submit", headers=emp_headers)
    assert response.status_code == 200

    response = await client.post(f"/periods/{PERIOD_ID}/approve", headers=mgr_headers)
    assert response.status_code == 200

    response = await client.post(f"/periods/{PERIOD_ID}/close", headers=mgr_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == PeriodStatus.CLOSED.value
    assert body["submission_status"] == SubmissionStatus.APPROVED.value
