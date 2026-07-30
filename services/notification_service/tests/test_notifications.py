import uuid

from tests.conftest import NOTIFICATION_ID


async def test_get_own_notifications(client, employee_token, test_notification):
    response = await client.get(
        "/notifications/", headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Табель согласован"
    assert body[0]["type"] == "APPROVAL"
    assert body[0]["is_read"] is False


async def test_notifications_are_self_scoped(client, teamlead_token, test_notification):
    response = await client.get(
        "/notifications/", headers={"Authorization": f"Bearer {teamlead_token}"}
    )
    assert response.status_code == 200
    assert response.json() == []  # чужие уведомления не видны


async def test_unread_only_filter(client, employee_token, test_notification, db_session):
    await client.post(
        f"/notifications/{NOTIFICATION_ID}/read",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    response = await client.get(
        "/notifications/?unread_only=true",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


async def test_read_notification(client, employee_token, test_notification):
    response = await client.post(
        f"/notifications/{NOTIFICATION_ID}/read",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    assert response.json()["is_read"] is True


async def test_read_foreign_notification_not_found(client, teamlead_token, test_notification):
    response = await client.post(
        f"/notifications/{NOTIFICATION_ID}/read",
        headers={"Authorization": f"Bearer {teamlead_token}"},
    )
    assert response.status_code == 404  # чужое неотличимо от несуществующего


async def test_read_unknown_notification(client, employee_token):
    response = await client.post(
        f"/notifications/{uuid.uuid4()}/read",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 404


async def test_read_all(client, employee_token, test_notification):
    response = await client.post(
        "/notifications/read-all",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 204

    response = await client.get(
        "/notifications/", headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert all(n["is_read"] for n in response.json())


async def test_notifications_require_auth(client):
    response = await client.get("/notifications/")
    assert response.status_code == 403  # HTTPBearer без заголовка


# ── Preferences ───────────────────────────────────────────────────────────────

async def test_preferences_defaults(client, employee_token):
    response = await client.get(
        "/notifications/preferences",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email_enabled"] is True
    assert body["push_enabled"] is True
    assert body["type_toggles"]["APPROVAL"] is True
    assert body["type_toggles"]["WEEKLY_DIGEST"] is False


async def test_preferences_patch_partial(client, employee_token):
    response = await client.patch(
        "/notifications/preferences",
        json={"type_toggles": {"CHAT": False}},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["type_toggles"]["CHAT"] is False
    assert body["type_toggles"]["APPROVAL"] is True  # неупомянутые ключи сохранены

    response = await client.patch(
        "/notifications/preferences",
        json={"email_enabled": False},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    body = response.json()
    assert body["email_enabled"] is False
    assert body["type_toggles"]["CHAT"] is False  # toggles не перезатёрты
