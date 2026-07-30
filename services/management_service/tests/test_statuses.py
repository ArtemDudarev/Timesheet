from tests.conftest import STATUS_ID


async def test_create_status(client, admin_token):
    response = await client.post(
        "/employee-statuses/",
        json={"name": "Уволен", "description": "Сотрудник уволен"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Уволен"


async def test_create_status_duplicate(client, admin_token, test_status):
    response = await client.post(
        "/employee-statuses/",
        json={"name": "Новый"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400


async def test_create_status_not_manager(client, employee_token):
    response = await client.post(
        "/employee-statuses/",
        json={"name": "Тест"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


async def test_create_status_no_auth(client):
    response = await client.post("/employee-statuses/", json={"name": "Тест"})
    assert response.status_code == 403


async def test_get_statuses(client, admin_token, test_status):
    response = await client.get("/employee-statuses/", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_get_statuses_as_manager(client, manager_token, test_status):
    """Чтение каталога статусов доступно с employee:list — без system:manage."""
    response = await client.get("/employee-statuses/", headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_get_statuses_not_viewer(client, employee_token):
    response = await client.get("/employee-statuses/", headers={"Authorization": f"Bearer {employee_token}"})
    assert response.status_code == 403


async def test_get_statuses_empty(client, admin_token):
    response = await client.get("/employee-statuses/", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert response.json() == []


async def test_get_status_by_id(client, admin_token, test_status):
    response = await client.get(
        f"/employee-statuses/{STATUS_ID}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Новый"


async def test_get_status_not_found(client, admin_token):
    import uuid
    response = await client.get(
        f"/employee-statuses/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


async def test_update_status(client, admin_token, test_status):
    response = await client.patch(
        f"/employee-statuses/{STATUS_ID}",
        json={"description": "Обновлённое описание"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Обновлённое описание"


async def test_update_status_not_found(client, admin_token):
    import uuid
    response = await client.patch(
        f"/employee-statuses/{uuid.uuid4()}",
        json={"name": "Несуществующий"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


async def test_update_status_name_conflict(client, admin_token, test_status, test_status_2):
    response = await client.patch(
        f"/employee-statuses/{STATUS_ID}",
        json={"name": "Активный"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400


async def test_delete_status(client, admin_token, test_status):
    response = await client.delete(
        f"/employee-statuses/{STATUS_ID}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200


async def test_delete_status_not_found(client, admin_token):
    import uuid
    response = await client.delete(
        f"/employee-statuses/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


async def test_delete_status_in_use(client, admin_token, test_employee):
    """Нельзя удалить статус, назначенный сотруднику → 400."""
    response = await client.delete(
        f"/employee-statuses/{STATUS_ID}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
