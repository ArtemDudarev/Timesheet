import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user
from src.models.refresh_token import RefreshToken
from src.schemas.session import SessionRead
from src.services.employee_service import UserService

router = APIRouter(prefix="/auth/sessions", tags=["Sessions"])


# Не-браузерные клиенты (подстрока в UA → отображаемое имя)
_NON_BROWSER_CLIENTS = [
    ("PostmanRuntime", "Postman"),
    ("insomnia", "Insomnia"),
    ("curl", "curl"),
    ("Wget", "Wget"),
    ("HTTPie", "HTTPie"),
    ("python-requests", "Python requests"),
    ("python-httpx", "Python httpx"),
    ("aiohttp", "aiohttp"),
    ("okhttp", "OkHttp"),
    ("axios", "axios"),
    ("Go-http-client", "Go client"),
    ("Java/", "Java client"),
    ("Dart/", "Dart client"),
    ("bot", "Бот"),
    ("Bot", "Бот"),
    ("spider", "Краулер"),
]


def _detect_browser(ua: str) -> str:
    """Порядок важен: многие браузеры подставляют Chrome/Safari в UA."""
    if "Edg" in ua or "EdgA" in ua or "EdgiOS" in ua:   return "Edge"
    if "OPR/" in ua or "Opera" in ua or "OPiOS" in ua:  return "Opera"
    if "YaBrowser" in ua:                               return "Yandex Browser"
    if "SamsungBrowser" in ua:                          return "Samsung Internet"
    if "Vivaldi" in ua:                                 return "Vivaldi"
    if "Firefox" in ua or "FxiOS" in ua:                return "Firefox"
    if "CriOS" in ua or "Chrome" in ua:                 return "Chrome"
    if "Safari" in ua:                                  return "Safari"
    return "Браузер"


def _detect_os(ua: str) -> str | None:
    if "iPhone" in ua:                          return "iPhone"
    if "iPad" in ua:                            return "iPad"
    if "iPod" in ua:                            return "iPod"
    if "Android" in ua:                         return "Android"
    if "Windows Phone" in ua:                   return "Windows Phone"
    if "Windows" in ua:                         return "Windows"
    if "CrOS" in ua:                            return "ChromeOS"
    if "Macintosh" in ua or "Mac OS X" in ua:   return "macOS"
    if "Linux" in ua:                           return "Linux"
    return None


def _parse_device(user_agent: str | None) -> str:
    if not user_agent:
        return "Неизвестное устройство"
    ua = user_agent

    for needle, label in _NON_BROWSER_CLIENTS:
        if needle in ua:
            return label

    browser = _detect_browser(ua)
    os_name = _detect_os(ua)
    if os_name:
        return f"{browser} · {os_name}"
    return browser


def _to_read(rt: RefreshToken) -> SessionRead:
    return SessionRead(
        id=rt.id,
        device=_parse_device(rt.user_agent),
        ip_address=rt.ip_address,
        created_at=rt.created_at,
        is_current=getattr(rt, "_is_current", False),
    )


@router.get("/", response_model=list[SessionRead])
async def list_sessions(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    current_token = request.cookies.get("refresh_token")
    svc = UserService(session)
    sessions = await svc.get_sessions(
        uuid.UUID(current_user["sub"]),
        current_token=current_token,
    )
    return [_to_read(s) for s in sessions]


@router.delete("/{session_id}", status_code=204)
async def revoke_session(
    session_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    svc = UserService(session)
    await svc.revoke_session(uuid.UUID(current_user["sub"]), session_id)


@router.delete("/", status_code=204)
async def revoke_all_sessions(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    current_token = request.cookies.get("refresh_token")
    svc = UserService(session)
    await svc.revoke_all_sessions(uuid.UUID(current_user["sub"]), keep_token=current_token)
