import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import require_permission
from src.schemas.permission import PermissionRead, RolePermissionsUpdate, RoleWithPermissionsRead
from src.services.role_permission_service import RolePermissionService

router = APIRouter(prefix="/admin", tags=["Admin"])

_system_manage = Depends(require_permission("system:manage"))


@router.get("/permissions", response_model=list[PermissionRead])
async def list_permissions(
    session: AsyncSession = Depends(get_async_session),
    _: dict = _system_manage,
):
    return await RolePermissionService(session).get_all_permissions()


@router.get("/roles", response_model=list[RoleWithPermissionsRead])
async def list_roles_with_permissions(
    session: AsyncSession = Depends(get_async_session),
    _: dict = _system_manage,
):
    return await RolePermissionService(session).get_roles_with_permissions()


@router.get("/roles/{role_id}/permissions", response_model=list[PermissionRead])
async def get_role_permissions(
    role_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _system_manage,
):
    return await RolePermissionService(session).get_permissions_for_role(role_id)


@router.put("/roles/{role_id}/permissions", response_model=list[PermissionRead])
async def set_role_permissions(
    role_id: uuid.UUID,
    data: RolePermissionsUpdate,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _system_manage,
):
    return await RolePermissionService(session).set_role_permissions(
        role_id, data.permission_codes
    )
