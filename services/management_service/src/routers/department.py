import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user, require_permission
from src.kafka.events import publish_department_created, publish_department_deleted, publish_department_updated
from src.models.department import Department
from src.models.employee import Employee
from src.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate

router = APIRouter(prefix="/departments", tags=["Departments"])

_manage = Depends(require_permission("directory:manage"))
_authenticated = Depends(get_current_user)


@router.get("/", response_model=list[DepartmentRead])
async def list_departments(
    session: AsyncSession = Depends(get_async_session),
    _: dict = _authenticated,
):
    result = await session.execute(select(Department).order_by(Department.name))
    return result.scalars().all()


@router.post("/", response_model=DepartmentRead, status_code=201)
async def create_department(
    data: DepartmentCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manage,
):
    dept = Department(**data.model_dump())
    session.add(dept)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Отдел с таким названием уже существует")
    await session.refresh(dept)
    await publish_department_created(request.app.state.kafka_producer, dept)
    return dept


@router.patch("/{department_id}", response_model=DepartmentRead)
async def update_department(
    department_id: uuid.UUID,
    data: DepartmentUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manage,
):
    dept = await session.get(Department, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Отдел не найден")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(dept, field, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Отдел с таким названием уже существует")
    await session.refresh(dept)
    await publish_department_updated(request.app.state.kafka_producer, dept)
    return dept


@router.delete("/{department_id}", status_code=204)
async def delete_department(
    department_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _manage,
):
    dept = await session.get(Department, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Отдел не найден")
    in_use = await session.scalar(
        select(func.count()).select_from(Employee).where(Employee.department_id == department_id)
    )
    if in_use:
        raise HTTPException(
            status_code=409,
            detail=f"Отдел назначен сотрудникам ({in_use}), удаление невозможно",
        )
    await session.delete(dept)
    await session.commit()
    await publish_department_deleted(request.app.state.kafka_producer, department_id)
