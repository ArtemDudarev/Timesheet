import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user
from src.models.refresh_token import RefreshToken
from src.schemas.session import SessionRead
from src.services.employee_service import UserService

router = APIRouter(prefix="/auth/sessions", tags=["Sessions"])


def _parse_device(user_agent: str | None) -> str:
    if not user_agent:
        return "Неизвестное устройство"
    ua = user_agent
    if "iPhone" in ua:
        browser = "Safari" if "Safari" in ua and "Chrome" not in ua else "Chrome"
        return f"{browser} · iPhone"
    if "iPad" in ua:
        return "Safari · iPad"
    if "Android" in ua:
        browser = "Chrome" if "Chrome" in ua else "Browser"
        return f"{browser} · Android"
    if "Windows" in ua:
        if "Edg" in ua:     return "Edge · Windows"
        if "Chrome" in ua:  return "Chrome · Windows"
        if "Firefox" in ua: return "Firefox · Windows"
        return "Browser · Windows"
    if "Macintosh" in ua or "Mac OS X" in ua:
        if "Chrome" in ua and "Edg" not in ua: return "Chrome · macOS"
        if "Firefox" in ua:                    return "Firefox · macOS"
        if "Safari" in ua:                     return "Safari · macOS"
        return "Browser · macOS"
    if "Linux" in ua:
        browser = "Chrome" if "Chrome" in ua else "Firefox" if "Firefox" in ua else "Browser"
        return f"{browser} · Linux"
    return "Браузер"


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
