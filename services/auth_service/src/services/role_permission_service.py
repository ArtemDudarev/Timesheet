import uuid

from fastapi import HTTPException
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.permission import Permission
from src.models.role import Role
from src.models.role_permission import role_permission as role_permission_table


class RolePermissionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_permissions(self) -> list[Permission]:
        result = await self.session.execute(
            select(Permission).order_by(Permission.code)
        )
        return list(result.scalars().all())

    async def get_roles_with_permissions(self) -> list[Role]:
        result = await self.session.execute(
            select(Role).options(selectinload(Role.permissions)).order_by(Role.name)
        )
        return list(result.scalars().all())

    async def get_permissions_for_role(self, role_id: uuid.UUID) -> list[Permission]:
        role = await self.session.get(
            Role, role_id, options=[selectinload(Role.permissions)]
        )
        if not role:
            raise HTTPException(status_code=404, detail="Роль не найдена")
        return list(role.permissions)

    async def set_role_permissions(
        self,
        role_id: uuid.UUID,
        permission_codes: list[str],
    ) -> list[Permission]:
        role = await self.session.get(
            Role, role_id, options=[selectinload(Role.permissions)]
        )
        if not role:
            raise HTTPException(status_code=404, detail="Роль не найдена")

        if not permission_codes:
            await self.session.execute(
                delete(role_permission_table).where(
                    role_permission_table.c.role_id == role_id
                )
            )
            await self.session.commit()
            return []

        perms_result = await self.session.execute(
            select(Permission).where(Permission.code.in_(permission_codes))
        )
        permissions = list(perms_result.scalars().all())

        found_codes = {p.code for p in permissions}
        missing = set(permission_codes) - found_codes
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Неизвестные коды разрешений: {', '.join(sorted(missing))}",
            )

        # Защита: нельзя убрать system:manage у всех ролей одновременно
        if "system:manage" not in permission_codes:
            result = await self.session.execute(
                select(Role)
                .join(role_permission_table, role_permission_table.c.role_id == Role.id)
                .join(Permission, Permission.id == role_permission_table.c.permission_id)
                .where(Permission.code == "system:manage", Role.id != role_id)
            )
            if result.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=400,
                    detail="Нельзя убрать system:manage — других ролей с этим правом нет",
                )

        await self.session.execute(
            delete(role_permission_table).where(
                role_permission_table.c.role_id == role_id
            )
        )
        await self.session.execute(
            insert(role_permission_table),
            [{"role_id": role_id, "permission_id": p.id} for p in permissions],
        )
        await self.session.commit()

        result = await self.session.execute(
            select(Permission)
            .join(role_permission_table, role_permission_table.c.permission_id == Permission.id)
            .where(role_permission_table.c.role_id == role_id)
            .order_by(Permission.code)
        )
        return list(result.scalars().all())
