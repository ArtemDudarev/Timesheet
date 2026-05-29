from tests.conftest import USER_ID, EMPLOYEE_ROLE_ID


async def test_get_employee_roles_success(client, test_user):
    """GET /employee-roles/employee/{id} → 200, роли пользователя."""
    response = await client.get(f"/employee-roles/employee/{USER_ID}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["role_id"] == str(EMPLOYEE_ROLE_ID)
    assert data[0]["employee_id"] == str(USER_ID)


async def test_get_employee_roles_empty(client):
    """Пользователь без ролей (или несуществующий) → 200, пустой список."""
    import uuid
    response = await client.get(f"/employee-roles/employee/{uuid.uuid4()}")
    assert response.status_code == 200
    assert response.json() == []
