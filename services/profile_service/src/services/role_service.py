from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.role import Role


class RoleService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> list[Role]:
        result = await self.session.execute(select(Role))
        return list(result.scalars().all())

    async def get_by_id(self, role_id: int) -> Role | None:
        result = await self.session.execute(
            select(Role).where(Role.role_id == role_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, role_name: str) -> Role | None:
        result = await self.session.execute(
            select(Role).where(Role.role_name == role_name)
        )
        return result.scalar_one_or_none()
