"""WebSocket: авторизация и broadcast через ConnectionManager."""
import uuid
from unittest.mock import AsyncMock

from src.ws import ConnectionManager

from tests.conftest import ALICE_ID, BOB_ID


async def test_broadcast_to_connected_users():
    manager = ConnectionManager()
    alice_ws = AsyncMock()
    bob_ws = AsyncMock()
    await manager.connect(ALICE_ID, alice_ws)
    await manager.connect(BOB_ID, bob_ws)

    await manager.send_to_users([BOB_ID], {"event": "message"})
    bob_ws.send_json.assert_awaited_once_with({"event": "message"})
    alice_ws.send_json.assert_not_awaited()


async def test_dead_connection_cleanup():
    manager = ConnectionManager()
    dead_ws = AsyncMock()
    dead_ws.send_json.side_effect = RuntimeError("connection closed")
    await manager.connect(ALICE_ID, dead_ws)

    await manager.send_to_users([ALICE_ID], {"event": "message"})
    # Мёртвое соединение вычищено — повторная отправка не дергает сокет
    dead_ws.send_json.reset_mock()
    await manager.send_to_users([ALICE_ID], {"event": "message"})
    dead_ws.send_json.assert_not_awaited()


async def test_disconnect_removes_user():
    manager = ConnectionManager()
    ws = AsyncMock()
    await manager.connect(ALICE_ID, ws)
    manager.disconnect(ALICE_ID, ws)
    await manager.send_to_users([ALICE_ID], {"event": "message"})
    ws.send_json.assert_not_awaited()


async def test_multiple_connections_same_user():
    manager = ConnectionManager()
    ws1, ws2 = AsyncMock(), AsyncMock()
    await manager.connect(ALICE_ID, ws1)
    await manager.connect(ALICE_ID, ws2)
    await manager.send_to_users([ALICE_ID], {"event": "message"})
    ws1.send_json.assert_awaited_once()
    ws2.send_json.assert_awaited_once()


async def test_ws_endpoint_rejects_bad_token(client):
    # Прямой вызов эндпоинта с невалидным токеном — соединение закрывается кодом 4401
    from src.routers.ws import chat_websocket

    ws = AsyncMock()
    await chat_websocket(ws, token="не-jwt")
    ws.close.assert_awaited_once_with(code=4401)
    ws.accept.assert_not_awaited()


async def test_message_post_broadcasts(client, alice_token, project_channel, monkeypatch):
    from src.ws import manager as global_manager

    sent = []

    async def fake_send(user_ids, payload):
        sent.append((list(user_ids), payload))

    monkeypatch.setattr(global_manager, "send_to_users", fake_send)

    response = await client.post(
        f"/chat/channels/{uuid.UUID(str(project_channel.id))}/messages",
        json={"text": "Проверка broadcast"},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert response.status_code == 201
    assert len(sent) == 1
    recipients, payload = sent[0]
    assert recipients == [BOB_ID]  # автор исключён
    assert payload["event"] == "message"
    assert payload["message"]["text"] == "Проверка broadcast"
