import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user, require_permission
from src.kafka.events import publish_grade_created, publish_grade_deleted, publish_grade_updated
from src.models.employee import Employee
from src.models.grade import Grade
from src.schemas.grade import GradeCreate, GradeRead, GradeUpdate

router = APIRouter(prefix="/grades", tags=["Grades"])

_manage = Depends(require_permission("directory:manage"))
_authenticated = Depends(get_current_user)


@router.get("/", response_model=list[GradeRead])
async def list_grades(
    session: AsyncSession = Depends(get_async_session),
    _: dict = _authenticated,
):
    result = await session.execute(select(Grade).order_by(Grade.sort_order, Grade.name))
    return result.scalars().all()


@router.post("/", response_model=GradeRead, status_code=201)
async def create_grade(
    data: GradeCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manage,
):
    grade = Grade(**data.model_dump())
    session.add(grade)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Грейд с таким названием уже существует")
    await session.refresh(grade)
    await publish_grade_created(request.app.state.kafka_producer, grade)
    return grade


@router.patch("/{grade_id}", response_model=GradeRead)
async def update_grade(
    grade_id: uuid.UUID,
    data: GradeUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manage,
):
    grade = await session.get(Grade, grade_id)
    if not grade:
        raise HTTPException(status_code=404, detail="Грейд не найден")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(grade, field, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Грейд с таким названием уже существует")
    await session.refresh(grade)
    await publish_grade_updated(request.app.state.kafka_producer, grade)
    return grade


@router.delete("/{grade_id}", status_code=204)
async def delete_grade(
    grade_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manage,
):
    grade = await session.get(Grade, grade_id)
    if not grade:
        raise HTTPException(status_code=404, detail="Грейд не найден")
    in_use = await session.scalar(
        select(func.count()).select_from(Employee).where(Employee.grade_id == grade_id)
    )
    if in_use:
        raise HTTPException(
            status_code=409,
            detail=f"Грейд назначен сотрудникам ({in_use}), удаление невозможно",
        )
    await session.delete(grade)
    await session.commit()
    await publish_grade_deleted(request.app.state.kafka_producer, grade_id)
