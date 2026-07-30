import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user
from src.schemas.notification import (
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
    NotificationRead,
)
from src.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=list[NotificationRead])
async def get_notifications(
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    svc = NotificationService(session)
    return await svc.get_all(
        user_id=uuid.UUID(current_user["sub"]),
        unread_only=unread_only,
        skip=skip,
        limit=limit,
    )


@router.get("/preferences", response_model=NotificationPreferenceRead)
async def get_preferences(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    svc = NotificationService(session)
    return await svc.get_preferences(uuid.UUID(current_user["sub"]))


@router.patch("/preferences", response_model=NotificationPreferenceRead)
async def update_preferences(
    data: NotificationPreferenceUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    svc = NotificationService(session)
    prefs = await svc.update_preferences(uuid.UUID(current_user["sub"]), data)
    await session.commit()
    return prefs


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def read_all(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    svc = NotificationService(session)
    await svc.mark_all_read(uuid.UUID(current_user["sub"]))
    await session.commit()


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def read_notification(
    notification_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    svc = NotificationService(session)
    notification = await svc.mark_read(notification_id, uuid.UUID(current_user["sub"]))
    await session.commit()
    return notification
