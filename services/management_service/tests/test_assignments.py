import uuid
from tests.conftest import EMPLOYEE_ID, PROJECT_ID, PROJECT_ROLE_ID, ASSIGN_STATUS_REQ_ID, ASSIGN_STATUS_ID


async def test_create_assignment(client, manager_token, test_employee, test_project, test_project_role, test_assign_status_req):
    response = await client.post(
        f"/employees/{EMPLOYEE_ID}/assignments",
        json={
            "project_id": str(PROJECT_ID),
            "project_role_id": str(PROJECT_ROLE_ID),
            "assignment_status_id": str(ASSIGN_STATUS_REQ_ID),
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["project"]["name"] == "Тестовый проект"
    assert data["project_role"]["name"] == "Разработчик"
    assert data["assignment_status"]["name"] == "Заявка"


async def test_create_assignment_employee_not_found(client, manager_token, test_project, test_project_role, test_assign_status_req):
    response = await client.post(
        f"/employees/{uuid.uuid4()}/assignments",
        json={
            "project_id": str(PROJECT_ID),
            "project_role_id": str(PROJECT_ROLE_ID),
            "assignment_status_id": str(ASSIGN_STATUS_REQ_ID),
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_create_assignment_project_not_found(client, manager_token, test_employee, test_project_role, test_assign_status_req):
    response = await client.post(
        f"/employees/{EMPLOYEE_ID}/assignments",
        json={
            "project_id": str(uuid.uuid4()),
            "project_role_id": str(PROJECT_ROLE_ID),
            "assignment_status_id": str(ASSIGN_STATUS_REQ_ID),
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_create_assignment_project_role_not_found(client, manager_token, test_employee, test_project, test_assign_status_req):
    response = await client.post(
        f"/employees/{EMPLOYEE_ID}/assignments",
        json={
            "project_id": str(PROJECT_ID),
            "project_role_id": str(uuid.uuid4()),
            "assignment_status_id": str(ASSIGN_STATUS_REQ_ID),
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_create_assignment_not_manager(client, employee_token, test_employee, test_project, test_project_role, test_assign_status_req):
    response = await client.post(
        f"/employees/{EMPLOYEE_ID}/assignments",
        json={
            "project_id": str(PROJECT_ID),
            "project_role_id": str(PROJECT_ROLE_ID),
            "assignment_status_id": str(ASSIGN_STATUS_REQ_ID),
        },
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


async def test_update_assignment(client, manager_token, test_assignment, test_assign_status):
    assignment_id = test_assignment.id
    response = await client.patch(
        f"/employees/{EMPLOYEE_ID}/assignments/{assignment_id}",
        json={"assignment_status_id": str(ASSIGN_STATUS_ID)},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["assignment_status"]["code"] == "ACTIVE"


async def test_update_assignment_not_found(client, manager_token, test_employee):
    response = await client.patch(
        f"/employees/{EMPLOYEE_ID}/assignments/{uuid.uuid4()}",
        json={"assignment_status_id": str(ASSIGN_STATUS_ID)},
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
    response = await client.delete(
        f"/employees/{EMPLOYEE_ID}/assignments/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404
