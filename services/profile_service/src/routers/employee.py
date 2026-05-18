import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.services.employee_service import EmployeeService
from src.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeListRead

router = APIRouter(prefix="/employees", tags=["employees"])

@router.post("/", response_model=EmployeeRead, status_code=201)
async def create_employee(
    employee_in: EmployeeCreate,
    session: AsyncSession = Depends(get_async_session)
):
    service = EmployeeService(session)
    if await service.get_employee_by_email(employee_in.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return await service.create_employee(employee_in)

@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    service = EmployeeService(session)
    employee = await service.get_employee_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

@router.get("/", response_model=list[EmployeeRead])
async def get_employees(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session)
):
    service = EmployeeService(session)
    return await service.get_all(skip=skip, limit=limit)