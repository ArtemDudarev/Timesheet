from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from src.models.status import Status
from src.schemas.status import StatusCreate


async def get_all_statuses(session: AsyncSession):
    """Получение списка всех статусов"""
    result = await session.execute(select(Status))
    return result.scalars().all()


async def create_status(session: AsyncSession, status_data: StatusCreate):
    """Создание нового статуса с защитой от дублирования названий"""
    new_status = Status(**status_data.model_dump())
    
    try:
        session.add(new_status)
        await session.commit()
        await session.refresh(new_status)
        return new_status
        
    except IntegrityError as e:
        # Обязательно отменяем транзакцию, чтобы сессия не заблокировалась
        await session.rollback()
        
        error_msg = str(e.orig).lower()
        
        # Проверяем, что упало именно ограничение уникальности имени
        if "status_name_key" in error_msg or "name" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Статус с наименованием '{status_data.name}' уже существует"
            )
            
        # На случай других непредвиденных ошибок базы данных
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка целостности данных при создании статуса"
        )