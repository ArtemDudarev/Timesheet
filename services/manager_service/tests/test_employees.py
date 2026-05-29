from tests.conftest import EMPLOYEE_ID, EMPLOYEE_ROLE_ID, MANAGER_ROLE_ID, STATUS_ID, STATUS_2_ID


async def test_get_employees_list(client, manager_token, test_employee):
    response = await client.get("/employees/", headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["first_name"] == "Иван"


async def test_get_employees_empty(client, manager_token):
    response = await client.get("/employees/", headers={"Authorization": f"Bearer {manager_token}"})
    assert response.status_code == 200
    assert response.json() == []


async def test_get_employees_not_manager(client, employee_token):
    response = await client.get("/employees/", headers={"Authorization": f"Bearer {employee_token}"})
    assert response.status_code == 403


async def test_get_employee_by_id(client, manager_token, test_employee):
    response = await client.get(
        f"/employees/{EMPLOYEE_ID}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Иван"
    assert data["status"]["name"] == "Новый"


async def test_get_employee_not_found(client, manager_token):
    import uuid
    response = await client.get(
        f"/employees/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_update_employee_roles(client, manager_token, test_employee, manager_role):
    response = await client.patch(
        f"/employees/{EMPLOYEE_ID}/roles",
        json={"role_ids": [str(MANAGER_ROLE_ID), str(EMPLOYEE_ROLE_ID)]},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    roles = [r["name"] for r in response.json()["user"]["roles"]]
    assert "Менеджер" in roles
    assert "Сотрудник" in roles


async def test_update_employee_roles_invalid_role(client, manager_token, test_employee):
    import uuid
    response = await client.patch(
        f"/employees/{EMPLOYEE_ID}/roles",
        json={"role_ids": [str(uuid.uuid4())]},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_update_employee_roles_not_found(client, manager_token):
    import uuid
    response = await client.patch(
        f"/employees/{uuid.uuid4()}/roles",
        json={"role_ids": [str(EMPLOYEE_ROLE_ID)]},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_update_employee_status(client, manager_token, test_employee, test_status_2):
    response = await client.patch(
        f"/employees/{EMPLOYEE_ID}/status",
        json={"status_id": str(STATUS_2_ID)},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"]["name"] == "Активный"


async def test_update_employee_status_invalid(client, manager_token, test_employee):
    import uuid
    response = await client.patch(
        f"/employees/{EMPLOYEE_ID}/status",
        json={"status_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_update_employee_status_not_found(client, manager_token):
    import uuid
    response = await client.patch(
        f"/employees/{uuid.uuid4()}/status",
        json={"status_id": str(STATUS_ID)},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404
