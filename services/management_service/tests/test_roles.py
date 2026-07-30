from tests.conftest import MANAGER_ROLE_ID, EMPLOYEE_ROLE_ID


async def test_create_role(client, admin_token):
    response = await client.post(
        "/roles/",
        json={"name": "Аналитик", "description": "Системный аналитик"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Аналитик"


async def test_create_role_duplicate(client, admin_token, manager_role):
    response = await client.post(
        "/roles/",
        json={"name": "Менеджер"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400


async def test_create_role_not_manager(client, employee_token):
    response = await client.post(
        "/roles/",
        json={"name": "Тест"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


async def test_get_roles(client, admin_token, manager_role, employee_role):
    response = await client.get("/roles/", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_get_roles_as_manager(client, manager_token, manager_role, employee_role):
    """Чтение каталога ролей доступно с employee:list — без system:manage."""
    response = await client.get("/roles/", headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_get_roles_not_viewer(client, employee_token):
    response = await client.get("/roles/", headers={"Authorization": f"Bearer {employee_token}"})
    assert response.status_code == 403


async def test_get_roles_empty(client, admin_token):
    response = await client.get("/roles/", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert response.json() == []


async def test_get_role_by_id(client, admin_token, manager_role):
    response = await client.get(
        f"/roles/{MANAGER_ROLE_ID}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Менеджер"


async def test_get_role_not_found(client, admin_token):
    import uuid
    response = await client.get(
        f"/roles/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


async def test_update_role(client, admin_token, manager_role):
    response = await client.patch(
        f"/roles/{MANAGER_ROLE_ID}",
        json={"description": "Главный менеджер"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Главный менеджер"


async def test_update_role_not_found(client, admin_token):
    import uuid
    response = await client.patch(
        f"/roles/{uuid.uuid4()}",
        json={"name": "Призрак"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


async def test_update_role_name_conflict(client, admin_token, manager_role, employee_role):
    response = await client.patch(
        f"/roles/{MANAGER_ROLE_ID}",
        json={"name": "Сотрудник"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400


async def test_delete_role(client, admin_token, manager_role):
    response = await client.delete(
        f"/roles/{MANAGER_ROLE_ID}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200


async def test_delete_role_not_found(client, admin_token):
    import uuid
    response = await client.delete(
        f"/roles/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


async def test_delete_role_cascades_user_roles(client, admin_token, test_employee):
    """FK cascade: удаление роли каскадно удаляет записи user_role → 200."""
    response = await client.delete(
        f"/roles/{EMPLOYEE_ROLE_ID}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
