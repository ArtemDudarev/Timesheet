async def test_get_statuses_success(client, test_status, user_token):
    """Авторизованный запрос → 200, список содержит созданный статус."""
    response = await client.get(
        "/statuses/",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Новый"


async def test_get_statuses_empty(client, user_token):
    """Нет статусов в БД → 200, пустой список."""
    response = await client.get(
        "/statuses/",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


async def test_get_statuses_no_auth(client):
    """Без токена → 403."""
    response = await client.get("/statuses/")
    assert response.status_code == 403
