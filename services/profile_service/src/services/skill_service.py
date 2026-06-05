import uuid
from typing import List

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.skill import Skill, employee_skill


class SkillService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> List[Skill]:
        result = await self.db.execute(select(Skill).order_by(Skill.name))
        return list(result.scalars().all())

    async def update_employee_skills(
        self, employee_id: uuid.UUID, skill_ids: List[uuid.UUID]
    ) -> None:
        await self.db.execute(
            delete(employee_skill).where(employee_skill.c.employee_id == employee_id)
        )
        if skill_ids:
            await self.db.execute(
                insert(employee_skill),
                [{"employee_id": employee_id, "skill_id": sid} for sid in skill_ids],
            )
        await self.db.commit()
