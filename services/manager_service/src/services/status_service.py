import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.status import Status
from src.schemas.status import StatusCreate, StatusUpdate


class StatusService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, status_data: StatusCreate) -> Status:
        db_status = Status(**status_data.model_dump())

        try:
            self.session.add(db_status)
            await self.session.commit()
            await self.session.refresh(db_status)
            return db_status
        except IntegrityError as exc:
            await self.session.rollback()
            self._raise_status_integrity_error(exc, status_data.name)

    async def get_all(self) -> list[Status]:
        result = await self.session.execute(select(Status))
        return list(result.scalars().all())

    async def get_by_id(self, status_id: uuid.UUID) -> Status | None:
        result = await self.session.execute(
            select(Status).where(Status.id == status_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Status | None:
        result = await self.session.execute(
            select(Status).where(Status.name == name)
        )
        return result.scalar_one_or_none()

    async def update(self, db_status: Status, status_data: StatusUpdate) -> Status:
        update_data = status_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_status, field, value)

        try:
            await self.session.commit()
            await self.session.refresh(db_status)
            return db_status
        except IntegrityError as exc:
            await self.session.rollback()
            self._raise_status_integrity_error(exc, db_status.name)

    def _raise_status_integrity_error(self, exc: IntegrityError, name: str) -> None:
        error_msg = str(exc.orig).lower()

        if "name" in error_msg or "status" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Статус '{name}' уже существует",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Данные статуса конфликтуют с существующими записями",
        )


async def get_all_statuses(session: AsyncSession):
    service = StatusService(session)
    return await service.get_all()


async def create_status(session: AsyncSession, status_data: StatusCreate):
    service = StatusService(session)
    return await service.create(status_data)
