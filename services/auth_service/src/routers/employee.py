import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeLogin, EmployeeCreateSimple
from src.services.employee_service import EmployeeService
from src.database import get_async_session
from src.kafka.events import publish_employee_created

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: EmployeeCreate, 
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    service = EmployeeService(session)
    existing = await service.get_by_identity(payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Employee with this email or number already exists"
        )
    employee = await service.create_new_employee(payload)
    try:
        await publish_employee_created(request.app.state.kafka_producer, employee)
    except Exception:
        logger.exception("Failed to publish employee.created event")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сотрудник создан, но событие регистрации не отправлено в Kafka",
        )
    return employee

@router.post("/register/public", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
async def register_public(
    payload: EmployeeCreateSimple, 
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    service = EmployeeService(session)
    existing = await service.get_by_identity(payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Employee with this email already exists"
        )
    employee = await service.create_simple_employee(payload)
    try:
        await publish_employee_created(request.app.state.kafka_producer, employee)
    except Exception:
        logger.exception("Failed to publish employee.created event")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сотрудник создан, но событие регистрации не отправлено в Kafka",
        )
    return employee

@router.post("/login")
async def login(
    payload: EmployeeLogin, 
    session: AsyncSession = Depends(get_async_session)
):
    service = EmployeeService(session)
    identity = payload.email or payload.employee_number
    
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email or Employee Number required"
        )
        
    employee = await service.get_by_identity(identity)
    
    if not employee or f"hashed_{payload.password}" != employee.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid credentials"
        )
    
    return {
        "message": "Successfully logged in", 
        "employee_id": employee.id,
        "email": employee.email
    }
