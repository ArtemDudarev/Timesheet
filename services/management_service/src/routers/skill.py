import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user, require_permission
from src.kafka.events import publish_skill_created, publish_skill_deleted, publish_skill_updated
from src.models.skill import Skill
from src.schemas.skill import SkillCreate, SkillRead, SkillUpdate

router = APIRouter(prefix="/skills", tags=["Skills"])

_manage = Depends(require_permission("directory:manage"))
_authenticated = Depends(get_current_user)


@router.get("/", response_model=list[SkillRead])
async def list_skills(
    session: AsyncSession = Depends(get_async_session),
    _: dict = _authenticated,
):
    result = await session.execute(select(Skill).order_by(Skill.name))
    return result.scalars().all()


@router.post("/", response_model=SkillRead, status_code=201)
async def create_skill(
    data: SkillCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manage,
):
    skill = Skill(**data.model_dump())
    session.add(skill)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Навык с таким названием уже существует")
    await session.refresh(skill)
    await publish_skill_created(request.app.state.kafka_producer, skill)
    return skill


@router.patch("/{skill_id}", response_model=SkillRead)
async def update_skill(
    skill_id: uuid.UUID,
    data: SkillUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manage,
):
    skill = await session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Навык не найден")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(skill, field, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Навык с таким названием уже существует")
    await session.refresh(skill)
    await publish_skill_updated(request.app.state.kafka_producer, skill)
    return skill


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manage,
):
    skill = await session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Навык не найден")
    await session.delete(skill)
    await session.commit()
    await publish_skill_deleted(request.app.state.kafka_producer, skill_id)
