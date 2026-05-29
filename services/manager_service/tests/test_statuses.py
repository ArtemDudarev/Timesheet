from tests.conftest import STATUS_ID


async def test_create_status(client, manager_token):
    response = await client.post(
        "/statuses/",
        json={"name": "Уволен", "description": "Сотрудник уволен"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Уволен"


async def test_create_status_duplicate(client, manager_token, test_status):
    response = await client.post(
        "/statuses/",
        json={"name": "Новый"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 400


async def test_create_status_not_manager(client, employee_token):
    response = await client.post(
        "/statuses/",
        json={"name": "Тест"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


async def test_create_status_no_auth(client):
    response = await client.post("/statuses/", json={"name": "Тест"})
    assert response.status_code == 403


async def test_get_statuses(client, manager_token, test_status):
    response = await client.get("/statuses/", headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_get_statuses_empty(client, manager_token):
    response = await client.get("/statuses/", headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code == 200
    assert response.json() == []


async def test_get_status_by_id(client, manager_token, test_status):
    response = await client.get(
        f"/statuses/{STATUS_ID}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Новый"


async def test_get_status_not_found(client, manager_token):
    import uuid
    response = await client.get(
        f"/statuses/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_update_status(client, manager_token, test_status):
    response = await client.patch(
        f"/statuses/{STATUS_ID}",
        json={"description": "Обновлённое описание"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Обновлённое описание"


async def test_update_status_not_found(client, manager_token):
    import uuid
    response = await client.patch(
        f"/statuses/{uuid.uuid4()}",
        json={"name": "Несуществующий"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_update_status_name_conflict(client, manager_token, test_status, test_status_2):
    response = await client.patch(
        f"/statuses/{STATUS_ID}",
        json={"name": "Активный"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 400


async def test_delete_status(client, manager_token, test_status):
    response = await client.delete(
        f"/statuses/{STATUS_ID}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200


async def test_delete_status_not_found(client, manager_token):
    import uuid
    response = await client.delete(
        f"/statuses/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_delete_status_in_use(client, manager_token, test_employee):
    """Нельзя удалить статус, назначенный сотруднику → 400."""
    response = await client.delete(
        f"/statuses/{STATUS_ID}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 400
