from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid # Импортируем для типизации, если нужно

from src.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeLogin, EmployeeCreateSimple
from src.services.employee_service import EmployeeService
from src.database import get_async_session

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: EmployeeCreate, 
    session: AsyncSession = Depends(get_async_session)
):
    service = EmployeeService(session)
    
    # Проверка на существование (Email или Номер)
    # Мы ищем по email, но сервис внутри может искать по обоим полям
    existing = await service.get_by_identity(payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Employee with this email or number already exists"
        )
    
    # create_new_employee теперь ожидает, что в payload.role_id лежат UUID
    return await service.create_new_employee(payload)

@router.post("/login")
async def login(
    payload: EmployeeLogin, 
    session: AsyncSession = Depends(get_async_session)
):
    service = EmployeeService(session)
    
    # Определяем, что ввел пользователь (логин через email или табельный номер)
    identity = payload.email or payload.employee_number
    
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email or Employee Number required"
        )
        
    employee = await service.get_by_identity(identity)
    
    # Простая проверка пароля (в будущем заменим на passlib/bcrypt)
    if not employee or f"hashed_{payload.password}" != employee.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid credentials"
        )
    
    # employee.id теперь вернет объект UUID, который FastAPI автоматически 
    # превратит в строку в JSON-ответе
    return {
        "message": "Successfully logged in", 
        "employee_id": employee.id,
        "email": employee.email
    }

# --- НОВЫЙ МЕТОД (Для быстрой публичной регистрации) ---
@router.post("/register/public", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
async def register_public(
    payload: EmployeeCreateSimple, # Использует новую схему (только email и password)
    session: AsyncSession = Depends(get_async_session)
):
    service = EmployeeService(session)
    
    # Проверяем, не занята ли почта
    existing = await service.get_by_identity(payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Employee with this email already exists"
        )
    
    # Вызываем метод автоматической генерации
    return await service.create_simple_employee(payload)