import uuid
from tests.conftest import EMPLOYEE_ID, PROJECT_ID, PROJECT_STATUS_ID, create_test_token


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


# ── Обогащённая модель проекта (code/color/client/lead/budget_hours/deadline) ─

async def test_create_project_with_enriched_fields(
    client, manager_token, test_project_status, test_employee
):
    response = await client.post(
        "/projects/",
        json={
            "name": "Омниканальная платформа",
            "project_status_id": str(PROJECT_STATUS_ID),
            "code": "OMNI",
            "color": "#7C3AED",
            "client": "ООО Ритейл",
            "lead_id": str(EMPLOYEE_ID),
            "budget_hours": 1200,
            "deadline": "2026-12-31",
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "OMNI"
    assert body["color"] == "#7C3AED"
    assert body["client"] == "ООО Ритейл"
    assert body["lead"]["id"] == str(EMPLOYEE_ID)
    assert body["lead"]["first_name"] == "Иван"
    assert body["budget_hours"] == 1200
    assert body["deadline"] == "2026-12-31"


async def test_create_project_duplicate_code(
    client, manager_token, test_project_status
):
    payload = {
        "name": "Первый",
        "project_status_id": str(PROJECT_STATUS_ID),
        "code": "DUP",
    }
    response = await client.post(
        "/projects/", json=payload, headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == 201

    payload["name"] = "Второй"
    response = await client.post(
        "/projects/", json=payload, headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == 400
    assert "DUP" in response.json()["detail"]


async def test_create_project_unknown_lead(client, manager_token, test_project_status):
    response = await client.post(
        "/projects/",
        json={
            "name": "Без руководителя",
            "project_status_id": str(PROJECT_STATUS_ID),
            "lead_id": str(uuid.uuid4()),
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


async def test_update_project_enriched_fields(
    client, manager_token, test_project, test_employee
):
    response = await client.patch(
        f"/projects/{PROJECT_ID}",
        json={
            "code": "TEST",
            "client": "АО Клиент",
            "lead_id": str(EMPLOYEE_ID),
            "budget_hours": 500.5,
        },
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "TEST"
    assert body["client"] == "АО Клиент"
    assert body["lead"]["last_name"] == "Петров"
    assert body["budget_hours"] == 500.5


async def test_update_project_unknown_lead(client, manager_token, test_project):
    response = await client.patch(
        f"/projects/{PROJECT_ID}",
        json={"lead_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 404


# ── project:read достаточно для чтения, но не для изменения ───────────────────

async def test_get_projects_with_read_permission_only(client, test_project):
    token = create_test_token(str(uuid.uuid4()), ["Тимлид"], ["project:read"])
    response = await client.get(
        "/projects/", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = await client.get(
        f"/projects/{PROJECT_ID}", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


async def test_create_project_with_read_permission_forbidden(client, test_project_status):
    token = create_test_token(str(uuid.uuid4()), ["Тимлид"], ["project:read"])
    response = await client.post(
        "/projects/",
        json={"name": "Нельзя", "project_status_id": str(PROJECT_STATUS_ID)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
