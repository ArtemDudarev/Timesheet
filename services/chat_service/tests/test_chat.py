import uuid

from tests.conftest import BOB_ID, CAROL_ID, CHANNEL_ID


async def _send(client, token, text="Привет!", **extra):
    return await client.post(
        f"/chat/channels/{CHANNEL_ID}/messages",
        json={"text": text, **extra},
        headers={"Authorization": f"Bearer {token}"},
    )


# ── Каналы ────────────────────────────────────────────────────────────────────

async def test_get_channels_membership(client, alice_token, carol_token, project_channel):
    response = await client.get(
        "/chat/channels", headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Внутренний портал"

    response = await client.get(
        "/chat/channels", headers={"Authorization": f"Bearer {carol_token}"}
    )
    assert response.json() == []


async def test_dm_get_or_create(client, alice_token, bob_token, test_employees):
    response = await client.post(
        f"/chat/dms/{BOB_ID}", headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "DM"
    assert body["companion"]["first_name"] == "Борис"
    dm_id = body["id"]

    # Повторный вызов возвращает тот же канал (в т.ч. с другой стороны)
    response = await client.post(
        f"/chat/dms/{BOB_ID}", headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert response.json()["id"] == dm_id


async def test_dm_with_self_forbidden(client, alice_token, test_employees):
    from tests.conftest import ALICE_ID
    response = await client.post(
        f"/chat/dms/{ALICE_ID}", headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert response.status_code == 400


async def test_pin_and_mute_toggle(client, alice_token, project_channel):
    response = await client.post(
        f"/chat/channels/{CHANNEL_ID}/pin", headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert response.json()["pinned"] is True
    response = await client.post(
        f"/chat/channels/{CHANNEL_ID}/mute", headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert response.json()["muted"] is True
    # Повторный pin снимает закрепление
    response = await client.post(
        f"/chat/channels/{CHANNEL_ID}/pin", headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert response.json()["pinned"] is False


async def test_get_channel_members(client, alice_token, project_channel):
    response = await client.get(
        f"/chat/channels/{CHANNEL_ID}/members",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 200
    names = [m["first_name"] for m in response.json()]
    assert len(names) == 2 and "Алиса" in names


async def test_get_channel_members_foreign_not_found(client, carol_token, project_channel):
    response = await client.get(
        f"/chat/channels/{CHANNEL_ID}/members",
        headers={"Authorization": f"Bearer {carol_token}"},
    )
    assert response.status_code == 404


# ── Сообщения ─────────────────────────────────────────────────────────────────

async def test_send_and_list_messages(client, alice_token, bob_token, project_channel):
    assert (await _send(client, alice_token, "Первое")).status_code == 201
    assert (await _send(client, bob_token, "Второе")).status_code == 201

    response = await client.get(
        f"/chat/channels/{CHANNEL_ID}/messages",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 200
    texts = [m["text"] for m in response.json()]
    assert texts == ["Второе", "Первое"]  # новые сверху


async def test_messages_foreign_channel_not_found(client, carol_token, project_channel):
    response = await client.get(
        f"/chat/channels/{CHANNEL_ID}/messages",
        headers={"Authorization": f"Bearer {carol_token}"},
    )
    assert response.status_code == 404
    response = await _send(client, carol_token)
    assert response.status_code == 404


async def test_reply_to_message(client, alice_token, bob_token, project_channel):
    parent_id = (await _send(client, alice_token, "Вопрос")).json()["id"]
    response = await _send(client, bob_token, "Ответ", reply_to_id=parent_id)
    assert response.status_code == 201
    assert response.json()["reply_to_id"] == parent_id


async def test_approval_card_message(client, alice_token, project_channel):
    approval_id = str(uuid.uuid4())
    response = await _send(
        client, alice_token, None,
        related_approval_type="ABSENCE", related_approval_id=approval_id,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["related_approval_type"] == "ABSENCE"
    assert body["related_approval_id"] == approval_id


async def test_empty_message_rejected(client, alice_token, project_channel):
    response = await _send(client, alice_token, None)
    assert response.status_code == 422


async def test_edit_own_message(client, alice_token, bob_token, project_channel):
    message_id = (await _send(client, alice_token)).json()["id"]

    response = await client.patch(
        f"/chat/messages/{message_id}",
        json={"text": "Исправлено"},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 200
    assert response.json()["edited"] is True

    # Чужое сообщение править нельзя
    response = await client.patch(
        f"/chat/messages/{message_id}",
        json={"text": "Взлом"},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert response.status_code == 403


async def test_delete_own_message(client, alice_token, project_channel):
    message_id = (await _send(client, alice_token)).json()["id"]
    response = await client.delete(
        f"/chat/messages/{message_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 204

    response = await client.get(
        f"/chat/channels/{CHANNEL_ID}/messages",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.json() == []


async def test_cursor_pagination(client, alice_token, project_channel):
    for i in range(5):
        await _send(client, alice_token, f"msg-{i}")

    response = await client.get(
        f"/chat/channels/{CHANNEL_ID}/messages?limit=2",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    first_page = response.json()
    assert len(first_page) == 2

    before = first_page[-1]["created_at"]
    response = await client.get(
        f"/chat/channels/{CHANNEL_ID}/messages?limit=10&before={before}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    older = response.json()
    assert all(m["created_at"] < before for m in older)
    assert len(older) + len(first_page) <= 5 + 1  # без дублей (граница по <)
