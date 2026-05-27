import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.role import Role
from src.schemas.role import RoleCreate, RoleUpdate


class RoleService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, role_in: RoleCreate) -> Role:
        role = Role(
            name=role_in.name,
            description=role_in.description,
        )

        try:
            self.session.add(role)
            await self.session.commit()
            await self.session.refresh(role)
            return role
        except IntegrityError as exc:
            await self.session.rollback()
            self._raise_role_integrity_error(exc, role_in.name)

    async def get_all(self) -> list[Role]:
        result = await self.session.execute(select(Role))
        return list(result.scalars().all())

    async def get_by_id(self, role_id: uuid.UUID) -> Role | None:
        result = await self.session.execute(
            select(Role).where(Role.id == role_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Role | None:
        result = await self.session.execute(
            select(Role).where(Role.name == name)
        )
        return result.scalar_one_or_none()

    async def update(self, role: Role, role_in: RoleUpdate) -> Role:
        update_data = role_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(role, field, value)

        try:
            await self.session.commit()
            await self.session.refresh(role)
            return role
        except IntegrityError as exc:
            await self.session.rollback()
            self._raise_role_integrity_error(exc, role.name)

    async def delete(self, role: Role) -> None:
        try:
            await self.session.delete(role)
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Роль нельзя удалить, так как она назначена сотрудникам",
            )

    def _raise_role_integrity_error(self, exc: IntegrityError, name: str) -> None:
        error_msg = str(exc.orig).lower()

        if "name" in error_msg or "role" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Роль '{name}' уже существует",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Данные роли конфликтуют с существующими записями",
        )
