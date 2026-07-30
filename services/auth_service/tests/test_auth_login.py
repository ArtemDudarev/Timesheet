async def test_login_user_not_found(client):
    """Несуществующий email → 401."""
    response = await client.post("/auth/login", json={
        "email": "nobody@example.com",
        "password": "SomePass1!",
    })
    assert response.status_code == 401


async def test_login_wrong_password(client, regular_user):
    """Пользователь есть, пароль неверный → 401."""
    response = await client.post("/auth/login", json={
        "email": "employee@test.com",
        "password": "WrongPass1!",
    })
    assert response.status_code == 401


async def test_login_success(client, regular_user):
    """Верные данные → 200, в ответе есть access_token."""
    response = await client.post("/auth/login", json={
        "email": "employee@test.com",
        "password": "Employee1!",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["access_token"] != ""
    assert data["must_change_password"] is False


async def test_login_email_case_insensitive(client, regular_user):
    """Email при логине не чувствителен к регистру."""
    response = await client.post("/auth/login", json={
        "email": "EMPLOYEE@Test.COM",
        "password": "Employee1!",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_login_inactive_user(client, db_session, regular_user):
    """Деактивированный аккаунт → 403."""
    regular_user.is_active = False
    await db_session.flush()

    response = await client.post("/auth/login", json={
        "email": "employee@test.com",
        "password": "Employee1!",
    })
    assert response.status_code == 403
