import json

from tests.conftest import APPROVER_ID, CONTRACT_TYPE_ID, SIGNER_ID


async def _create_document(client, token, route=None, title="Договор подряда"):
    route = route or [
        {"employee_id": str(APPROVER_ID), "role": "APPROVER", "step_order": 1},
        {"employee_id": str(SIGNER_ID), "role": "SIGNER", "step_order": 2},
    ]
    return await client.post(
        "/documents/",
        data={
            "title": title,
            "type_id": str(CONTRACT_TYPE_ID),
            "route": json.dumps(route),
            "comment": "Прошу согласовать",
        },
        files={"file": ("contract.pdf", b"%PDF-1.4 test content", "application/pdf")},
        headers={"Authorization": f"Bearer {token}"},
    )


async def test_create_document(client, author_token, contract_type, test_employees):
    response = await _create_document(client, author_token)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "На подписании"
    assert body["file_size"] == len(b"%PDF-1.4 test content")
    assert len(body["route"]) == 2
    assert body["route"][0]["role"] == "APPROVER"
    assert body["route"][0]["status"] == "Ожидает"


async def test_create_document_bad_route(client, author_token, contract_type, test_employees):
    response = await client.post(
        "/documents/",
        data={"title": "X", "type_id": str(CONTRACT_TYPE_ID), "route": "не json"},
        files={"file": ("f.txt", b"data", "text/plain")},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert response.status_code == 422


async def test_full_signing_route(client, author_token, approver_token, signer_token,
                                  contract_type, test_employees):
    doc_id = (await _create_document(client, author_token)).json()["id"]

    # Подписант (шаг 2) не может действовать, пока не прошёл шаг 1
    response = await client.post(
        f"/documents/{doc_id}/sign", headers={"Authorization": f"Bearer {signer_token}"}
    )
    assert response.status_code == 403

    # Шаг 1: согласующий
    response = await client.post(
        f"/documents/{doc_id}/sign", headers={"Authorization": f"Bearer {approver_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "На подписании"  # маршрут ещё не завершён

    # Шаг 2: подписант — последний шаг, документ подписан
    response = await client.post(
        f"/documents/{doc_id}/sign", headers={"Authorization": f"Bearer {signer_token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "Подписан"
    assert all(s["status"] == "Подписано" for s in body["route"])


async def test_reject_breaks_route(client, author_token, approver_token, signer_token,
                                   contract_type, test_employees):
    doc_id = (await _create_document(client, author_token)).json()["id"]

    response = await client.post(
        f"/documents/{doc_id}/reject",
        json={"comment": "Неверная сумма в п. 3.1"},
        headers={"Authorization": f"Bearer {approver_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "Отклонён"
    assert body["route"][0]["comment"] == "Неверная сумма в п. 3.1"

    # Маршрут прерван — подписант больше не может действовать
    response = await client.post(
        f"/documents/{doc_id}/sign", headers={"Authorization": f"Bearer {signer_token}"}
    )
    assert response.status_code == 409


async def test_reject_requires_comment(client, author_token, approver_token,
                                       contract_type, test_employees):
    doc_id = (await _create_document(client, author_token)).json()["id"]
    response = await client.post(
        f"/documents/{doc_id}/reject",
        json={},
        headers={"Authorization": f"Bearer {approver_token}"},
    )
    assert response.status_code == 422


async def test_access_control(client, author_token, outsider_token, admin_token,
                              contract_type, test_employees):
    doc_id = (await _create_document(client, author_token)).json()["id"]

    # Посторонний не видит документ (404, не 403 — не раскрываем существование)
    response = await client.get(
        f"/documents/{doc_id}", headers={"Authorization": f"Bearer {outsider_token}"}
    )
    assert response.status_code == 404
    response = await client.get(
        "/documents/", headers={"Authorization": f"Bearer {outsider_token}"}
    )
    assert response.json() == []

    # document:read_any видит всё
    response = await client.get(
        f"/documents/{doc_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200


async def test_pending_filter(client, author_token, approver_token, signer_token,
                              contract_type, test_employees):
    await _create_document(client, author_token)

    # Текущий шаг у согласующего — у него документ в pending
    response = await client.get(
        "/documents/?filter=pending", headers={"Authorization": f"Bearer {approver_token}"}
    )
    assert len(response.json()) == 1
    # У подписанта шаг ещё не наступил
    response = await client.get(
        "/documents/?filter=pending", headers={"Authorization": f"Bearer {signer_token}"}
    )
    assert response.json() == []


async def test_file_download_roundtrip(client, author_token, contract_type, test_employees):
    doc_id = (await _create_document(client, author_token)).json()["id"]
    response = await client.get(
        f"/documents/{doc_id}/file", headers={"Authorization": f"Bearer {author_token}"}
    )
    assert response.status_code == 200
    assert response.content == b"%PDF-1.4 test content"


async def test_file_download_forbidden_for_outsider(client, author_token, outsider_token,
                                                    contract_type, test_employees):
    doc_id = (await _create_document(client, author_token)).json()["id"]
    response = await client.get(
        f"/documents/{doc_id}/file", headers={"Authorization": f"Bearer {outsider_token}"}
    )
    assert response.status_code == 404
