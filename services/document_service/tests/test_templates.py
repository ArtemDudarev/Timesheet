from tests.conftest import CONTRACT_TYPE_ID


async def _create_template(client, token):
    return await client.post(
        "/document-templates/",
        data={"title": "Шаблон договора", "type_id": str(CONTRACT_TYPE_ID)},
        files={"file": ("template.docx", b"DOCX template body", "application/octet-stream")},
        headers={"Authorization": f"Bearer {token}"},
    )


async def test_create_template_requires_permission(client, author_token, contract_type):
    response = await _create_template(client, author_token)
    assert response.status_code == 403


async def test_template_crud(client, admin_token, author_token, contract_type):
    response = await _create_template(client, admin_token)
    assert response.status_code == 201
    template_id = response.json()["id"]

    # Список и скачивание доступны любому авторизованному
    response = await client.get(
        "/document-templates/", headers={"Authorization": f"Bearer {author_token}"}
    )
    assert len(response.json()) == 1

    response = await client.get(
        f"/document-templates/{template_id}/file",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert response.status_code == 200
    assert response.content == b"DOCX template body"

    # Удаление — только с правом
    response = await client.delete(
        f"/document-templates/{template_id}",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert response.status_code == 403

    response = await client.delete(
        f"/document-templates/{template_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204


async def test_document_types(client, author_token, contract_type):
    response = await client.get(
        "/document-types/", headers={"Authorization": f"Bearer {author_token}"}
    )
    assert response.status_code == 200
    assert response.json()[0]["code"] == "CONTRACT"
