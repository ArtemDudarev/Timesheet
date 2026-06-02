import uuid
from tests.conftest import PROJECT_ID, PROJECT_STATUS_ID


async def test_create_project(client, manager_token, test_project_status):
    response = await client.post(
        "/projects/",
        json={"name": "Новый портал", "project_status_id": str(PROJECT_STATUS_ID)},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Новый портал"
    assert response.json()["project_status"]["name"] == "Активный"


async def test_create_project_duplicate(client, manager_token, test_project):
    response = await client.post(
        "/projects/",
        json={"name": "Тестовый проект", "project_status_id": str(PROJECT_STATUS_ID)},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 400


async def test_create_project_not_manager(client, employee_token):
    response = await client.post(
        "/projects/",
        json={"name": "Запрещённый", "project_status_id": str(PROJECT_STATUS_ID)},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


async def test_create_project_invalid_status(client, manager_token):
    response = await client.post(
        "/projects/",
        json={"name": "Плохой", "project_status_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_get_projects(client, manager_token, test_project):
    response = await client.get("/projects/", headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_get_projects_empty(client, manager_token):
    response = await client.get("/projects/", headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code == 200
    assert response.json() == []


async def test_get_project_by_id(client, manager_token, test_project):
    response = await client.get(
        f"/projects/{PROJECT_ID}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Тестовый проект"


async def test_get_project_not_found(client, manager_token):
    response = await client.get(
        f"/projects/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_update_project(client, manager_token, test_project, test_project_status):
    response = await client.patch(
        f"/projects/{PROJECT_ID}",
        json={"project_status_id": str(PROJECT_STATUS_ID)},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["project_status"]["code"] == "ACTIVE"


async def test_update_project_not_found(client, manager_token):
    response = await client.patch(
        f"/projects/{uuid.uuid4()}",
        json={"name": "Призрак"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_delete_project(client, manager_token, test_project):
    response = await client.delete(
        f"/projects/{PROJECT_ID}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200


async def test_delete_project_not_found(client, manager_token):
    response = await client.delete(
        f"/projects/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_delete_project_cascades_assignments(client, manager_token, test_assignment):
    """FK cascade: удаление проекта каскадно удаляет назначения → 200."""
    response = await client.delete(
        f"/projects/{PROJECT_ID}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
