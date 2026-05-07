from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeLogin
from src.services.employee_service import EmployeeService
from src.database import get_async_session # Предполагается наличие этого генератора

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: EmployeeCreate, 
    session: AsyncSession = Depends(get_async_session)
):
    service = EmployeeService(session)
    
    # Проверяем, не занят ли email или номер
    existing = await service.get_by_identity(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Employee already exists")
    
    return await service.create_new_employee(payload)

@router.post("/login")
async def login(
    payload: EmployeeLogin, 
    session: AsyncSession = Depends(get_async_session)
):
    service = EmployeeService(session)
    identity = payload.email or payload.employee_number
    
    if not identity:
        raise HTTPException(status_code=400, detail="Email or Employee Number required")
        
    employee = await service.get_by_identity(identity)
    
    # В реальности тут будет: if not employee or not verify_password(payload.password, employee.hashed_password):
    if not employee or f"hashed_{payload.password}" != employee.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {"message": "Successfully logged in", "employee_id": employee.id}