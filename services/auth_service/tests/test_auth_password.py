import uuid

from tests.conftest import REGULAR_USER_ID


async def test_change_password_success(client, regular_user, regular_token):
    """Верный текущий пароль → смена → 204."""
    response = await client.post(
        "/auth/password/change",
        json={
            "current_password": "Employee1!",
            "new_password": "NewPass1!",
        },
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert response.status_code == 204


async def test_change_password_wrong_current(client, regular_user, regular_token):
    """Неверный текущий пароль → 400."""
    response = await client.post(
        "/auth/password/change",
        json={
            "current_password": "WrongPass1!",
            "new_password": "NewPass1!",
        },
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert response.status_code == 400


async def test_change_password_no_auth(client):
    """Без токена → 403 (HTTPBearer отклоняет до обработки запроса)."""
    response = await client.post(
        "/auth/password/change",
        json={
            "current_password": "Employee1!",
            "new_password": "NewPass1!",
        },
    )
    assert response.status_code == 403


async def test_change_password_same_password(client, regular_user, regular_token):
    """Новый пароль совпадает с текущим → 422."""
    response = await client.post(
        "/auth/password/change",
        json={
            "current_password": "Employee1!",
            "new_password": "Employee1!",
        },
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert response.status_code == 422


async def test_change_password_weak_new(client, regular_user, regular_token):
    """Слабый новый пароль → 422."""
    response = await client.post(
        "/auth/password/change",
        json={
            "current_password": "Employee1!",
            "new_password": "weak",
        },
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert response.status_code == 422


async def test_reset_password_success(client, manager_token, regular_user):
    """Менеджер сбрасывает пароль → 200 + temp_password."""
    response = await client.post(
        f"/auth/password/reset/{REGULAR_USER_ID}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "temp_password" in data
    assert len(data["temp_password"]) > 0


async def test_reset_password_not_manager(client, regular_token, regular_user):
    """Обычный сотрудник не может сбросить пароль → 403."""
    response = await client.post(
        f"/auth/password/reset/{REGULAR_USER_ID}",
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert response.status_code == 403


async def test_reset_password_not_found(client, manager_token):
    """Несуществующий user_id → 404."""
    response = await client.post(
        f"/auth/password/reset/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_reset_password_no_auth(client, regular_user):
    """Без токена → 403 (HTTPBearer отклоняет до проверки ролей)."""
    response = await client.post(f"/auth/password/reset/{REGULAR_USER_ID}")
    assert response.status_code == 403
