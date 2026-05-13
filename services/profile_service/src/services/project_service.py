from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.project import Project
from src.schemas.project import (
    ProjectCreate,
    ProjectUpdate
)


class ProjectService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(
        self,
        project_id: UUID
    ) -> Project | None:
        """Поиск проекта по ID"""

        query = (
            select(Project)
            .where(Project.id == project_id)
        )

        result = await self.session.execute(query)

        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        project_name: str
    ) -> Project | None:
        """Поиск проекта по названию"""

        query = (
            select(Project)
            .where(Project.project_name == project_name)
        )

        result = await self.session.execute(query)

        return result.scalar_one_or_none()

    async def get_all_projects(self) -> list[Project]:
        """Получение списка всех проектов"""

        query = select(Project)

        result = await self.session.execute(query)

        return list(result.scalars().all())

    async def create_project(
        self,
        data: ProjectCreate
    ) -> Project:
        """Создание нового проекта"""

        new_project = Project(
            project_name=data.project_name,
            project_status=data.project_status
        )

        try:
            self.session.add(new_project)

            await self.session.commit()

            await self.session.refresh(new_project)

            return new_project

        except IntegrityError as e:
            await self.session.rollback()

            error_msg = str(e.orig).lower()

            if "project_name" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Проект '{data.project_name}' уже существует"
                )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ошибка при создании проекта"
            )

    async def update_project(
        self,
        project_id: UUID,
        data: ProjectUpdate
    ) -> Project | None:
        """Обновление проекта"""

        project = await self.get_by_id(project_id)

        if not project:
            return None

        if data.project_name is not None:
            project.project_name = data.project_name

        if data.project_status is not None:
            project.project_status = data.project_status

        try:
            await self.session.commit()

            await self.session.refresh(project)

            return project

        except IntegrityError:
            await self.session.rollback()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ошибка при обновлении проекта"
            )

    async def delete_project(
        self,
        project_id: UUID
    ) -> bool:
        """Удаление проекта"""

        project = await self.get_by_id(project_id)

        if not project:
            return False

        await self.session.delete(project)

        await self.session.commit()

        return True