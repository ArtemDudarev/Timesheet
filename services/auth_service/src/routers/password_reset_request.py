import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import require_permission
from src.kafka.events import publish_password_reset_requested
from src.limiter import RESET_REQUEST_RATE_LIMIT, limiter
from src.models.password_reset_request import ResetRequestStatus
from src.schemas.employee import PasswordResetResponse
from src.schemas.password_reset_request import (
    PasswordResetRequestCreate,
    PasswordResetRequestRead,
)
from src.services.password_reset_request_service import PasswordResetRequestService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/password/reset-requests", tags=["Password Reset Requests"])

_manager = Depends(require_permission("user:reset_password"))


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(RESET_REQUEST_RATE_LIMIT)
async def create_reset_request(
    request: Request,
    payload: PasswordResetRequestCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Публичный эндпоинт «забыли пароль»: заявка уходит в очередь менеджера.

    Ответ всегда 202 — независимо от того, найден ли аккаунт, чтобы не раскрывать
    существование учётных записей."""
    service = PasswordResetRequestService(session)
    reset_request, created = await service.create(payload.identifier)
    if created:
        try:
            await publish_password_reset_requested(
                request.app.state.kafka_producer, reset_request
            )
            await session.commit()
        except HTTPException:
            raise
        except Exception:
            await session.rollback()
            logger.exception("Failed to publish password_reset.requested event")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Не удалось отправить заявку. Попробуйте снова.",
            )
    return {"detail": "Если аккаунт найден, заявка передана менеджеру"}


@router.get("/", response_model=list[PasswordResetRequestRead])
async def get_reset_requests(
    status_filter: ResetRequestStatus = Query(ResetRequestStatus.PENDING, alias="status"),
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manager,
):
    service = PasswordResetRequestService(session)
    return await service.get_all(status_filter=status_filter, skip=skip, limit=limit)


@router.post("/{request_id}/resolve", response_model=PasswordResetResponse)
async def resolve_reset_request(
    request_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = _manager,
):
    service = PasswordResetRequestService(session)
    temp_password = await service.resolve(
        request_id, resolved_by=uuid.UUID(current_user["sub"])
    )
    return PasswordResetResponse(temp_password=temp_password)


@router.post("/{request_id}/cancel", response_model=PasswordResetRequestRead)
async def cancel_reset_request(
    request_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = _manager,
):
    service = PasswordResetRequestService(session)
    return await service.cancel(request_id, resolved_by=uuid.UUID(current_user["sub"]))
