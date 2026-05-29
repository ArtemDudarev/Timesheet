from tests.conftest import PROJECT_ID


async def test_create_project(client, manager_token):
    response = await client.post(
        "/project/",
        json={"name": "Новый портал", "status": "Активный"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Новый портал"
    assert response.json()["status"] == "Активный"


async def test_create_project_duplicate(client, manager_token, test_project):
    response = await client.post(
        "/project/",
        json={"name": "Тестовый проект"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 400


async def test_create_project_not_manager(client, employee_token):
    response = await client.post(
        "/project/",
        json={"name": "Запрещённый"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


async def test_create_project_invalid_status(client, manager_token):
    response = await client.post(
        "/project/",
        json={"name": "Плохой", "status": "НесуществующийСтатус"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 422


async def test_get_projects(client, manager_token, test_project):
    response = await client.get("/project/", headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_get_projects_empty(client, manager_token):
    response = await client.get("/project/", headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code == 200
    assert response.json() == []


async def test_get_project_by_id(client, manager_token, test_project):
    response = await client.get(
        f"/project/{PROJECT_ID}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Тестовый проект"


async def test_get_project_not_found(client, manager_token):
    import uuid
    response = await client.get(
        f"/project/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_update_project(client, manager_token, test_project):
    response = await client.patch(
        f"/project/{PROJECT_ID}",
        json={"status": "Завершён"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Завершён"


async def test_update_project_not_found(client, manager_token):
    import uuid
    response = await client.patch(
        f"/project/{uuid.uuid4()}",
        json={"name": "Призрак"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_delete_project(client, manager_token, test_project):
    response = await client.delete(
        f"/project/{PROJECT_ID}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200


async def test_delete_project_not_found(client, manager_token):
    import uuid
    response = await client.delete(
        f"/project/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_delete_project_cascades_assignments(client, manager_token, test_assignment):
    """FK cascade: удаление проекта каскадно удаляет назначения → 200."""
    response = await client.delete(
        f"/project/{PROJECT_ID}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
