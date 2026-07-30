import uuid

import pytest

from src.limiter import limiter
from src.models.password_reset_request import PasswordResetRequest, ResetRequestStatus

from tests.conftest import REGULAR_USER_ID


@pytest.fixture(autouse=True)
def _reset_limiter():
    """Сбрасываем rate-limit (3/minute на create) между тестами."""
    limiter.reset()


# ── Create (public) ───────────────────────────────────────────────────────────

async def test_create_request_existing_user(client, db_session, regular_user):
    response = await client.post(
        "/auth/password/reset-requests/",
        json={"identifier": "employee@test.com"},
    )
    assert response.status_code == 202
    assert "заявка передана менеджеру" in response.json()["detail"]

    result = await db_session.get(
        PasswordResetRequest,
        (await _get_single_request_id(db_session)),
    )
    assert result.user_id == REGULAR_USER_ID
    assert result.status == ResetRequestStatus.PENDING


async def test_create_request_unknown_user_same_response(client, db_session):
    response = await client.post(
        "/auth/password/reset-requests/",
        json={"identifier": "ghost@test.com"},
    )
    assert response.status_code == 202
    assert "заявка передана менеджеру" in response.json()["detail"]

    request = await db_session.get(
        PasswordResetRequest,
        (await _get_single_request_id(db_session)),
    )
    assert request.user_id is None  # аккаунт не найден, но заявка сохранена


async def test_create_request_dedup_pending(client, db_session, regular_user, manager_token):
    for _ in range(2):
        response = await client.post(
            "/auth/password/reset-requests/",
            json={"identifier": "employee@test.com"},
        )
        assert response.status_code == 202

    response = await client.get(
        "/auth/password/reset-requests/",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert len(response.json()) == 1  # дубль не создан


async def test_create_request_dedup_case_insensitive(client, db_session, regular_user, manager_token):
    """Регистронезависимый email не должен плодить вторую заявку на того же пользователя."""
    for identifier in ("employee@test.com", "EMPLOYEE@Test.COM"):
        response = await client.post(
            "/auth/password/reset-requests/",
            json={"identifier": identifier},
        )
        assert response.status_code == 202

    response = await client.get(
        "/auth/password/reset-requests/",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert len(response.json()) == 1


async def test_create_request_rate_limited(client, regular_user):
    for _ in range(3):
        await client.post(
            "/auth/password/reset-requests/",
            json={"identifier": "employee@test.com"},
        )
    response = await client.post(
        "/auth/password/reset-requests/",
        json={"identifier": "employee@test.com"},
    )
    assert response.status_code == 429


# ── List (manager) ────────────────────────────────────────────────────────────

async def test_list_requires_permission(client, regular_token):
    response = await client.get(
        "/auth/password/reset-requests/",
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert response.status_code == 403


async def test_list_pending_by_default(client, db_session, regular_user, manager_token):
    await client.post(
        "/auth/password/reset-requests/", json={"identifier": "employee@test.com"}
    )
    response = await client.get(
        "/auth/password/reset-requests/",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["identifier"] == "employee@test.com"
    assert body[0]["status"] == "Ожидает"


# ── Resolve ───────────────────────────────────────────────────────────────────

async def test_resolve_returns_temp_password(client, db_session, regular_user, manager_token):
    await client.post(
        "/auth/password/reset-requests/", json={"identifier": "employee@test.com"}
    )
    request_id = await _get_single_request_id(db_session)

    response = await client.post(
        f"/auth/password/reset-requests/{request_id}/resolve",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["temp_password"]

    request = await db_session.get(PasswordResetRequest, request_id)
    assert request.status == ResetRequestStatus.RESOLVED
    assert request.resolved_by is not None
    await db_session.refresh(regular_user)
    assert regular_user.must_change_password is True


async def test_resolve_twice_conflict(client, db_session, regular_user, manager_token):
    await client.post(
        "/auth/password/reset-requests/", json={"identifier": "employee@test.com"}
    )
    request_id = await _get_single_request_id(db_session)
    headers = {"Authorization": f"Bearer {manager_token}"}

    await client.post(f"/auth/password/reset-requests/{request_id}/resolve", headers=headers)
    response = await client.post(
        f"/auth/password/reset-requests/{request_id}/resolve", headers=headers
    )
    assert response.status_code == 409


async def test_resolve_unknown_user_conflict(client, db_session, manager_token):
    await client.post(
        "/auth/password/reset-requests/", json={"identifier": "ghost@test.com"}
    )
    request_id = await _get_single_request_id(db_session)

    response = await client.post(
        f"/auth/password/reset-requests/{request_id}/resolve",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 409


async def test_resolve_not_found(client, manager_token):
    response = await client.post(
        f"/auth/password/reset-requests/{uuid.uuid4()}/resolve",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


# ── Cancel ────────────────────────────────────────────────────────────────────

async def test_cancel_request(client, db_session, manager_token):
    await client.post(
        "/auth/password/reset-requests/", json={"identifier": "ghost@test.com"}
    )
    request_id = await _get_single_request_id(db_session)

    response = await client.post(
        f"/auth/password/reset-requests/{request_id}/cancel",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Отменена"


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_single_request_id(db_session) -> uuid.UUID:
    from sqlalchemy import select

    result = await db_session.execute(select(PasswordResetRequest.id))
    ids = list(result.scalars().all())
    assert len(ids) == 1
    return ids[0]
