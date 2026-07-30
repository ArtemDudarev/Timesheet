import logging
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from src.database import async_session_maker
from src.security import decode_token
from src.services.chat_service import ChatService
from src.ws import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat WebSocket"])


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket, token: str = Query(...)):
    """События сервера: message. События клиента: typing, read —
    транслируются остальным участникам канала."""
    try:
        payload = decode_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        await websocket.close(code=4401)
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("event")
            channel_id_raw = data.get("channel_id")
            if event not in ("typing", "read") or not channel_id_raw:
                continue
            try:
                channel_id = uuid.UUID(str(channel_id_raw))
            except ValueError:
                continue
            async with async_session_maker() as session:
                svc = ChatService(session)
                try:
                    await svc.get_membership(channel_id, user_id)
                except Exception:
                    continue  # не участник — молча игнорируем
                recipients = [
                    m for m in await svc.get_member_ids(channel_id) if m != user_id
                ]
            await manager.send_to_users(recipients, {
                "event": event,
                "channel_id": str(channel_id),
                "employee_id": str(user_id),
            })
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, websocket)
