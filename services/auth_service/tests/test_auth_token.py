async def test_refresh_success(client, refresh_token_val):
    """Валидный refresh token → 200 + новый access token."""
    response = await client.post(
        "/auth/refresh",
        cookies={"refresh_token": refresh_token_val},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["access_token"] != ""


async def test_refresh_no_cookie(client):
    """Без cookie → 401."""
    response = await client.post("/auth/refresh")
    assert response.status_code == 401


async def test_refresh_invalid_token(client):
    """Несуществующий токен → 401."""
    response = await client.post(
        "/auth/refresh",
        cookies={"refresh_token": "invalid-token-value"},
    )
    assert response.status_code == 401


async def test_refresh_rotates_token(client, refresh_token_val):
    """Каждый refresh выдаёт новый cookie (ротация)."""
    refresh_resp = await client.post(
        "/auth/refresh",
        cookies={"refresh_token": refresh_token_val},
    )
    assert refresh_resp.status_code == 200
    new_cookie = refresh_resp.cookies.get("refresh_token")
    assert new_cookie is not None
    assert new_cookie != refresh_token_val


async def test_logout_success(client, refresh_token_val):
    """Валидный токен → logout → 204."""
    response = await client.post(
        "/auth/logout",
        cookies={"refresh_token": refresh_token_val},
    )
    assert response.status_code == 204


async def test_logout_no_cookie(client):
    """Без cookie → тоже 204 (graceful)."""
    response = await client.post("/auth/logout")
    assert response.status_code == 204


async def test_refresh_after_logout(client, refresh_token_val):
    """После logout refresh token недействителен → 401."""
    await client.post("/auth/logout", cookies={"refresh_token": refresh_token_val})

    response = await client.post(
        "/auth/refresh",
        cookies={"refresh_token": refresh_token_val},
    )
    assert response.status_code == 401
