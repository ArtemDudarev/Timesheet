import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user
from src.schemas.chat import ChannelRead, EmployeeShort, MessageCreate, MessageRead, MessageUpdate
from src.services.chat_service import ChatService
from src.ws import manager

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/channels", response_model=list[ChannelRead])
async def get_channels(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    return await ChatService(session).get_channels(uuid.UUID(current_user["sub"]))


@router.post("/dms/{employee_id}", response_model=ChannelRead)
async def get_or_create_dm(
    employee_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    caller_id = uuid.UUID(current_user["sub"])
    svc = ChatService(session)
    channel = await svc.get_or_create_dm(caller_id, employee_id)
    await session.commit()
    channels = await svc.get_channels(caller_id)
    return next(c for c in channels if c.id == channel.id)


@router.get("/channels/{channel_id}/members", response_model=list[EmployeeShort])
async def get_channel_members(
    channel_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    return await ChatService(session).get_members(channel_id, uuid.UUID(current_user["sub"]))


@router.get("/channels/{channel_id}/messages", response_model=list[MessageRead])
async def get_messages(
    channel_id: uuid.UUID,
    before: datetime | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    """Курсорная пагинация: новые сверху; before — created_at последнего полученного."""
    return await ChatService(session).get_messages(
        channel_id, uuid.UUID(current_user["sub"]), before=before, limit=limit
    )


@router.post(
    "/channels/{channel_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    channel_id: uuid.UUID,
    data: MessageCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    caller_id = uuid.UUID(current_user["sub"])
    svc = ChatService(session)
    message = await svc.create_message(channel_id, caller_id, data)
    await session.commit()

    recipients = [m for m in await svc.get_member_ids(channel_id) if m != caller_id]
    await manager.send_to_users(recipients, {
        "event": "message",
        "channel_id": str(channel_id),
        "message": MessageRead.model_validate(message).model_dump(mode="json"),
    })
    return message


@router.patch("/messages/{message_id}", response_model=MessageRead)
async def update_message(
    message_id: uuid.UUID,
    data: MessageUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    svc = ChatService(session)
    message = await svc.update_message(
        message_id, uuid.UUID(current_user["sub"]), data.text
    )
    await session.commit()
    return message


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    await ChatService(session).delete_message(message_id, uuid.UUID(current_user["sub"]))
    await session.commit()


@router.post("/channels/{channel_id}/pin", response_model=ChannelRead)
async def toggle_pin(
    channel_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    caller_id = uuid.UUID(current_user["sub"])
    svc = ChatService(session)
    await svc.toggle_pin(channel_id, caller_id)
    await session.commit()
    channels = await svc.get_channels(caller_id)
    return next(c for c in channels if c.id == channel_id)


@router.post("/channels/{channel_id}/mute", response_model=ChannelRead)
async def toggle_mute(
    channel_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    caller_id = uuid.UUID(current_user["sub"])
    svc = ChatService(session)
    await svc.toggle_mute(channel_id, caller_id)
    await session.commit()
    channels = await svc.get_channels(caller_id)
    return next(c for c in channels if c.id == channel_id)
