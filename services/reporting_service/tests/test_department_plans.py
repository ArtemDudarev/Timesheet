import uuid

from tests.conftest import DEPARTMENT_ID, PLAN_ID


async def test_create_plan(client, manager_token, test_department):
    response = await client.post(
        "/department-plans/",
        json={
            "department_id": str(DEPARTMENT_ID),
            "year": 2026,
            "month": 7,
            "planned_hours": 168,
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 201
    assert response.json()["planned_hours"] == 168.0


async def test_create_plan_duplicate(client, manager_token, test_plan):
    response = await client.post(
        "/department-plans/",
        json={
            "department_id": str(DEPARTMENT_ID),
            "year": 2026,
            "month": 6,
            "planned_hours": 100,
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 409


async def test_create_plan_unknown_department(client, manager_token):
    response = await client.post(
        "/department-plans/",
        json={
            "department_id": str(uuid.uuid4()),
            "year": 2026,
            "month": 7,
            "planned_hours": 168,
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_plans_require_manage_permission(client, reader_token, test_plan):
    response = await client.get(
        "/department-plans/",
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert response.status_code == 403  # report:read недостаточно, нужен report:manage


async def test_update_plan(client, manager_token, test_plan):
    response = await client.patch(
        f"/department-plans/{PLAN_ID}",
        json={"planned_hours": 152},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["planned_hours"] == 152.0


async def test_delete_plan(client, manager_token, test_plan):
    response = await client.delete(
        f"/department-plans/{PLAN_ID}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 204

    response = await client.get(
        "/department-plans/",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.json() == []
