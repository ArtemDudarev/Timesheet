from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.project_role import ProjectRole
from ..schemas.project_role import ProjectRoleCreate, ProjectRoleUpdate


class ProjectRoleService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ProjectRole]:
        query = select(ProjectRole).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, role_id: UUID) -> ProjectRole | None:
        return await self.session.get(ProjectRole, role_id)

    async def create(self, role_data: ProjectRoleCreate) -> ProjectRole:
        db_role = ProjectRole(
            name=role_data.name,
            description=role_data.description,
        )

        try:
            self.session.add(db_role)
            await self.session.commit()
            await self.session.refresh(db_role)
            return db_role
        except IntegrityError as exc:
            await self.session.rollback()
            self._raise_project_role_integrity_error(exc, role_data.name)

    async def update(self, role_id: UUID, role_data: ProjectRoleUpdate) -> ProjectRole | None:
        db_role = await self.get_by_id(role_id)
        if not db_role:
            return None

        update_data = role_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_role, key, value)

        try:
            await self.session.commit()
            await self.session.refresh(db_role)
            return db_role
        except IntegrityError as exc:
            await self.session.rollback()
            self._raise_project_role_integrity_error(exc, db_role.name)

    async def delete(self, role_id: UUID) -> bool:
        db_role = await self.get_by_id(role_id)
        if not db_role:
            return False

        try:
            await self.session.delete(db_role)
            await self.session.commit()
            return True
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Проектную роль нельзя удалить, так как она используется",
            )

    def _raise_project_role_integrity_error(
        self,
        exc: IntegrityError,
        name: str | None,
    ) -> None:
        error_msg = str(exc.orig).lower()

        if "name" in error_msg or "project_role" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Проектная роль '{name}' уже существует",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Данные проектной роли конфликтуют с существующими записями",
        )
