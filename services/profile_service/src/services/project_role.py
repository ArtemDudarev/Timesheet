from uuid import UUID

from sqlalchemy import select
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
        self.session.add(db_role)
        await self.session.commit()
        await self.session.refresh(db_role)
        return db_role

    async def update(self, role_id: UUID, role_data: ProjectRoleUpdate) -> ProjectRole | None:
        db_role = await self.get_by_id(role_id)
        if not db_role:
            return None

        update_data = role_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_role, key, value)

        await self.session.commit()
        await self.session.refresh(db_role)
        return db_role

    async def delete(self, role_id: UUID) -> bool:
        db_role = await self.get_by_id(role_id)
        if not db_role:
            return False

        await self.session.delete(db_role)
        await self.session.commit()
        return True
