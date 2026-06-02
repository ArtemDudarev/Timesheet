import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user, require_roles
from src.kafka.events import publish_user_created
from src.limiter import limiter
from src.schemas.employee import PasswordChange, PasswordResetResponse, TokenResponse, UserCreate, UserLogin, UserRead
from src.security import create_access_token
from src.services.employee_service import UserService

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = Depends(require_roles("Менеджер")),
):
    service = UserService(session)
    if await service.get_by_identity(payload.email):
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
    user = await service.create_user(payload)
    try:
        await publish_user_created(request.app.state.kafka_producer, user)
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("Failed to publish user.created event")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Не удалось отправить событие регистрации. Попробуйте снова.",
        )
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    payload: UserLogin,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
):
    service = UserService(session)
    identity = payload.email or payload.number
    user = await service.get_by_identity(identity)
    if not user:
        service.dummy_verify()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учётные данные",
        )
    if not service.verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учётные данные",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учётная запись деактивирована",
        )

    access_token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "roles": [role.name for role in user.roles],
        "is_active": user.is_active,
    })
    refresh_token = await service.create_refresh_token(user.id)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="strict",
        secure=COOKIE_SECURE,
        max_age=30 * 24 * 60 * 60,
    )
    return TokenResponse(access_token=access_token, must_change_password=user.must_change_password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token не найден")

    service = UserService(session)
    user, new_refresh_token = await service.rotate_refresh_token(token)

    access_token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "roles": [role.name for role in user.roles],
        "is_active": user.is_active,
    })
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        samesite="strict",
        secure=COOKIE_SECURE,
        max_age=30 * 24 * 60 * 60,
    )
    return TokenResponse(access_token=access_token, must_change_password=user.must_change_password)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
    _: dict = Depends(get_current_user),
):
    token = request.cookies.get("refresh_token")
    if token:
        service = UserService(session)
        await service.revoke_refresh_token(token)
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        samesite="strict",
        secure=COOKIE_SECURE,
    )


@router.post("/password/reset/{user_id}", response_model=PasswordResetResponse)
async def reset_password(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    _: dict = Depends(require_roles("Менеджер")),
):
    service = UserService(session)
    temp_password = await service.reset_password(user_id)
    return PasswordResetResponse(temp_password=temp_password)


@router.post("/password/change", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChange,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    service = UserService(session)
    await service.change_password(
        uuid.UUID(current_user["sub"]),
        payload.current_password,
        payload.new_password,
    )
