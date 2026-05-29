from tests.conftest import PROJECT_ROLE_ID


async def test_create_project_role(client, manager_token):
    response = await client.post(
        "/project-roles/",
        json={"name": "Тимлид", "description": "Руководитель команды"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Тимлид"


async def test_create_project_role_duplicate(client, manager_token, test_project_role):
    response = await client.post(
        "/project-roles/",
        json={"name": "Разработчик"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 400


async def test_create_project_role_not_manager(client, employee_token):
    response = await client.post(
        "/project-roles/",
        json={"name": "Тест"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


async def test_get_project_roles(client, manager_token, test_project_role):
    response = await client.get(
        "/project-roles/",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_get_project_roles_pagination(client, manager_token, test_project_role):
    response = await client.get(
        "/project-roles/?skip=0&limit=1",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_get_project_roles_skip(client, manager_token, test_project_role):
    response = await client.get(
        "/project-roles/?skip=10&limit=100",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


async def test_get_project_role_by_id(client, manager_token, test_project_role):
    response = await client.get(
        f"/project-roles/{PROJECT_ROLE_ID}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Разработчик"


async def test_get_project_role_not_found(client, manager_token):
    import uuid
    response = await client.get(
        f"/project-roles/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_update_project_role(client, manager_token, test_project_role):
    response = await client.patch(
        f"/project-roles/{PROJECT_ROLE_ID}",
        json={"description": "Fullstack разработчик"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Fullstack разработчик"


async def test_update_project_role_not_found(client, manager_token):
    import uuid
    response = await client.patch(
        f"/project-roles/{uuid.uuid4()}",
        json={"name": "Призрак"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_delete_project_role(client, manager_token, test_project_role):
    response = await client.delete(
        f"/project-roles/{PROJECT_ROLE_ID}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 204


async def test_delete_project_role_not_found(client, manager_token):
    import uuid
    response = await client.delete(
        f"/project-roles/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_delete_project_role_in_use(client, manager_token, test_assignment):
    """Нельзя удалить проектную роль, используемую в назначении → 400."""
    response = await client.delete(
        f"/project-roles/{PROJECT_ROLE_ID}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 400
