import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.employee_project import EmployeeProject
from src.models.project import Project
from src.models.project_role import ProjectRole
from src.schemas.assignment import AssignmentCreate, AssignmentUpdate


class AssignmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        assignment_id: uuid.UUID,
        employee_id: uuid.UUID,
    ) -> Optional[EmployeeProject]:
        result = await self.db.execute(
            select(EmployeeProject).where(
                EmployeeProject.id == assignment_id,
                EmployeeProject.employee_id == employee_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        employee_id: uuid.UUID,
        data: AssignmentCreate,
    ) -> EmployeeProject:
        await self._validate_project(data.project_id)
        await self._validate_role(data.project_role_id)

        assignment = EmployeeProject(
            employee_id=employee_id,
            project_id=data.project_id,
            project_role_id=data.project_role_id,
            start_date=data.start_date,
            end_date=data.end_date,
            status=data.status,
        )
        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment, attribute_names=["project", "project_role"])
        return assignment

    async def update(
        self,
        assignment: EmployeeProject,
        data: AssignmentUpdate,
    ) -> EmployeeProject:
        update_data = data.model_dump(exclude_unset=True)

        if "project_role_id" in update_data:
            await self._validate_role(update_data["project_role_id"])

        for field, value in update_data.items():
            setattr(assignment, field, value)

        await self.db.commit()
        await self.db.refresh(assignment, attribute_names=["project", "project_role"])
        return assignment

    async def delete(self, assignment: EmployeeProject) -> None:
        await self.db.delete(assignment)
        await self.db.commit()

    async def _validate_project(self, project_id: uuid.UUID) -> None:
        project = await self.db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Проект не найден",
            )

    async def _validate_role(self, project_role_id: uuid.UUID) -> None:
        role = await self.db.get(ProjectRole, project_role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Проектная роль не найдена",
            )
