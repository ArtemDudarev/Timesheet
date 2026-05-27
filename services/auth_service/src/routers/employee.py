import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import require_roles
from src.kafka.events import publish_user_created
from src.schemas.employee import TokenResponse, UserCreate, UserLogin, UserRead, UserRegister
from src.security import create_access_token
from src.services.employee_service import UserService

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
    except Exception:
        logger.exception("Failed to publish user.created event")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Пользователь создан, но событие регистрации не отправлено в Kafka",
        )
    return user


@router.post("/register/public", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_public(
    payload: UserRegister,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    service = UserService(session)
    if await service.get_by_identity(payload.email):
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
    user = await service.register_user(payload)
    try:
        await publish_user_created(request.app.state.kafka_producer, user)
    except Exception:
        logger.exception("Failed to publish user.created event")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Пользователь создан, но событие регистрации не отправлено в Kafka",
        )
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLogin,
    session: AsyncSession = Depends(get_async_session),
):
    service = UserService(session)
    identity = payload.email or payload.number
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать email или номер сотрудника",
        )

    user = await service.get_by_identity(identity)
    if not user or not service.verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учётные данные",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учётная запись деактивирована",
        )

    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "roles": [role.name for role in user.roles],
        "is_active": user.is_active,
    })
    return TokenResponse(access_token=token)
