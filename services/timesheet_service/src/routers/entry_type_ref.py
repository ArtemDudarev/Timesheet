import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user
from src.models.entry_type_ref import EntryTypeRef
from src.schemas.entry_type_ref import EntryTypeRefResponse

router = APIRouter(prefix="/entry-types", tags=["Entry Types"])


@router.get("/", response_model=list[EntryTypeRefResponse])
async def get_entry_types(
    session: AsyncSession = Depends(get_async_session),
    _: dict = Depends(get_current_user),
):
    result = await session.execute(select(EntryTypeRef).order_by(EntryTypeRef.name))
    return list(result.scalars().all())


@router.get("/{entry_type_id}", response_model=EntryTypeRefResponse)
async def get_entry_type(
    entry_type_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    _: dict = Depends(get_current_user),
):
    t = await session.get(EntryTypeRef, entry_type_id)
    if not t:
        raise HTTPException(status_code=404, detail="Тип трудозатрат не найден")
    return t
