from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..services.employee_service import EmployeeService
from ..schemas.employee import EmployeeCreate, EmployeeResponse

router = APIRouter(prefix="/employees", tags=["employees"])


@router.post("/", response_model=EmployeeResponse)
async def create_employee(employee_in: EmployeeCreate, db: AsyncSession = Depends(get_db)):
    service = EmployeeService(db)
    
    if await service.get_employee_by_email(employee_in.employee_email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    return await service.create_employee(employee_in)


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(employee_id: int, db: AsyncSession = Depends(get_db)):
    service = EmployeeService(db)
    employee = await service.get_employee_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee