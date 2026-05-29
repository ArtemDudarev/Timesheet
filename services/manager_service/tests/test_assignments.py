from tests.conftest import EMPLOYEE_ID, PROJECT_ID, PROJECT_ROLE_ID


async def test_create_assignment(client, manager_token, test_employee, test_project, test_project_role):
    response = await client.post(
        f"/employees/{EMPLOYEE_ID}/assignments",
        json={
            "project_id": str(PROJECT_ID),
            "project_role_id": str(PROJECT_ROLE_ID),
            "status": "Заявка",
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["project"]["name"] == "Тестовый проект"
    assert data["project_role"]["name"] == "Разработчик"
    assert data["status"] == "Заявка"


async def test_create_assignment_employee_not_found(client, manager_token, test_project, test_project_role):
    import uuid
    response = await client.post(
        f"/employees/{uuid.uuid4()}/assignments",
        json={"project_id": str(PROJECT_ID), "project_role_id": str(PROJECT_ROLE_ID)},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_create_assignment_project_not_found(client, manager_token, test_employee, test_project_role):
    import uuid
    response = await client.post(
        f"/employees/{EMPLOYEE_ID}/assignments",
        json={"project_id": str(uuid.uuid4()), "project_role_id": str(PROJECT_ROLE_ID)},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_create_assignment_project_role_not_found(client, manager_token, test_employee, test_project):
    import uuid
    response = await client.post(
        f"/employees/{EMPLOYEE_ID}/assignments",
        json={"project_id": str(PROJECT_ID), "project_role_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_create_assignment_not_manager(client, employee_token, test_employee, test_project, test_project_role):
    response = await client.post(
        f"/employees/{EMPLOYEE_ID}/assignments",
        json={"project_id": str(PROJECT_ID), "project_role_id": str(PROJECT_ROLE_ID)},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


async def test_update_assignment(client, manager_token, test_assignment):
    from tests.conftest import EMPLOYEE_ID
    assignment_id = test_assignment.id
    response = await client.patch(
        f"/employees/{EMPLOYEE_ID}/assignments/{assignment_id}",
        json={"status": "Снят с проекта"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Снят с проекта"


async def test_update_assignment_not_found(client, manager_token, test_employee):
    import uuid
    response = await client.patch(
        f"/employees/{EMPLOYEE_ID}/assignments/{uuid.uuid4()}",
        json={"status": "Продлён"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_delete_assignment(client, manager_token, test_assignment):
    assignment_id = test_assignment.id
    response = await client.delete(
        f"/employees/{EMPLOYEE_ID}/assignments/{assignment_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 204


async def test_delete_assignment_not_found(client, manager_token, test_employee):
    import uuid
    response = await client.delete(
        f"/employees/{EMPLOYEE_ID}/assignments/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404
