from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.project import Project
from src.models.project_status import ProjectStatus
from src.schemas.project import ProjectCreate, ProjectUpdate

class ProjectService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, project_id: UUID) -> Project | None:
        query = select(Project).where(Project.id == project_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Project | None:
        query = select(Project).where(Project.name == name)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all_projects(self) -> list[Project]:
        query = select(Project)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_project(self, data: ProjectCreate) -> Project:
        await self._validate_status(data.status_id)
        new_project = Project(
            name=data.name,
            status_id=data.status_id,
            start_date=data.start_date,
            end_date=data.end_date,
        )
        try:
            self.session.add(new_project)
            await self.session.commit()
            await self.session.refresh(new_project, attribute_names=["project_status"])
            return new_project
        except IntegrityError as e:
            await self.session.rollback()
            error_msg = str(e.orig).lower()
            if "name" in error_msg or "project" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Проект '{data.name}' уже существует"
                )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ошибка при создании проекта")

    async def update_project(self, project_id: UUID, data: ProjectUpdate) -> Project | None:
        project = await self.get_by_id(project_id)
        if not project:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "status_id" in update_data:
            await self._validate_status(update_data["status_id"])
        for field, value in update_data.items():
            setattr(project, field, value)

        try:
            await self.session.commit()
            await self.session.refresh(project, attribute_names=["project_status"])
            return project
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ошибка при обновлении проекта")

    async def _validate_status(self, status_id: UUID) -> None:
        s = await self.session.get(ProjectStatus, status_id)
        if not s:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Статус проекта не найден",
            )

    async def delete_project(self, project_id: UUID) -> bool:
        project = await self.get_by_id(project_id)
        if not project:
            return False
        try:
            await self.session.delete(project)
            await self.session.commit()
            return True
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Проект нельзя удалить, так как он используется в связанных данных",
            )
