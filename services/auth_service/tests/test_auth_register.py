from tests.conftest import EMPLOYEE_ROLE_ID


async def test_register_success(client, manager_token, employee_role):
    """Менеджер регистрирует нового пользователя → 201."""
    response = await client.post(
        "/auth/register",
        json={
            "email": "newuser@test.com",
            "password": "NewUser1!",
            "role_ids": [str(EMPLOYEE_ROLE_ID)],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert "id" in data


async def test_register_no_auth(client):
    """Без токена → 403 (HTTPBearer отклоняет до проверки ролей)."""
    response = await client.post(
        "/auth/register",
        json={
            "email": "x@test.com",
            "password": "Pass1234!",
            "role_ids": [str(EMPLOYEE_ROLE_ID)],
        },
    )
    assert response.status_code == 403


async def test_register_not_manager(client, regular_token, regular_user, employee_role):
    """Обычный сотрудник не может регистрировать → 403."""
    response = await client.post(
        "/auth/register",
        json={
            "email": "another@test.com",
            "password": "Pass1234!",
            "role_ids": [str(EMPLOYEE_ROLE_ID)],
        },
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert response.status_code == 403


async def test_register_duplicate_email(client, manager_token, regular_user):
    """Email уже занят → 400."""
    response = await client.post(
        "/auth/register",
        json={
            "email": "employee@test.com",  # уже есть в БД
            "password": "Pass1234!",
            "role_ids": [str(EMPLOYEE_ROLE_ID)],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 400


async def test_register_weak_password(client, manager_token, employee_role):
    """Слабый пароль не проходит валидацию → 422."""
    response = await client.post(
        "/auth/register",
        json={
            "email": "new@test.com",
            "password": "weak",
            "role_ids": [str(EMPLOYEE_ROLE_ID)],
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 422
