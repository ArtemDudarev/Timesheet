from tests.conftest import USER_ID, OTHER_USER_ID


async def test_get_employee_success(client, test_user, user_token):
    """GET /employees/{id} с валидным токеном → 200, данные сотрудника."""
    response = await client.get(
        f"/employees/{USER_ID}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Иван"
    assert data["last_name"] == "Петров"
    assert data["status"]["name"] == "Новый"
    assert data["user"]["email"] == "employee@test.com"


async def test_get_employee_not_found(client, user_token):
    """Несуществующий employee_id → 404."""
    import uuid
    response = await client.get(
        f"/employees/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 404


async def test_get_employee_no_auth(client, test_user):
    """Без токена → 403."""
    response = await client.get(f"/employees/{USER_ID}")
    assert response.status_code == 403


async def test_update_employee_self(client, test_user, user_token):
    """Сотрудник редактирует свой профиль → 200, поля обновились."""
    response = await client.patch(
        f"/employees/{USER_ID}",
        json={"first_name": "Алексей", "phone": "+79001234567"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Алексей"
    assert data["phone"] == "+79001234567"


async def test_update_employee_as_manager(client, test_user, manager_token):
    """Менеджер редактирует профиль другого сотрудника → 200."""
    response = await client.patch(
        f"/employees/{USER_ID}",
        json={"last_name": "Иванов"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["last_name"] == "Иванов"


async def test_update_employee_other_user_forbidden(client, test_user, other_token):
    """Чужой сотрудник без роли менеджера → 403."""
    response = await client.patch(
        f"/employees/{USER_ID}",
        json={"first_name": "Хакер"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


async def test_update_employee_not_found(client, manager_token):
    """PATCH несуществующего сотрудника → 404."""
    import uuid
    response = await client.patch(
        f"/employees/{uuid.uuid4()}",
        json={"first_name": "Призрак"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_update_employee_no_auth(client, test_user):
    """Без токена → 403."""
    response = await client.patch(
        f"/employees/{USER_ID}",
        json={"first_name": "Никто"},
    )
    assert response.status_code == 403


async def test_update_employee_partial(client, test_user, user_token):
    """PATCH только одного поля — остальные не затронуты."""
    response = await client.patch(
        f"/employees/{USER_ID}",
        json={"address": "г. Москва, ул. Тестовая, 1"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["address"] == "г. Москва, ул. Тестовая, 1"
    assert data["first_name"] == "Иван"
