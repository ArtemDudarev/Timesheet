import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.schemas.role import RoleRead
from src.services.role_service import RoleService


router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=list[RoleRead])
async def get_roles(
    session: AsyncSession = Depends(get_async_session),
):
    service = RoleService(session)
    return await service.get_all()


@router.get("/{role_id}", response_model=RoleRead)
async def get_role(
    role_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
):
    service = RoleService(session)
    role = await service.get_by_id(role_id)

    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")

    return role
