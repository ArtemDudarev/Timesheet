import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.assignment_status import AssignmentStatus
from src.models.employee import Employee
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
        await self._validate_employee_not_fired(employee_id)
        await self._validate_project(data.project_id)
        await self._validate_role(data.project_role_id)
        await self._validate_status(data.assignment_status_id)

        assignment = EmployeeProject(
            employee_id=employee_id,
            project_id=data.project_id,
            project_role_id=data.project_role_id,
            start_date=data.start_date,
            end_date=data.end_date,
            status_id=data.assignment_status_id,
        )
        self.db.add(assignment)
        await self.db.flush()
        assignment_id = assignment.id
        await self.db.commit()
        return await self._reload(assignment_id)

    async def update(
        self,
        assignment: EmployeeProject,
        data: AssignmentUpdate,
    ) -> EmployeeProject:
        update_data = data.model_dump(exclude_unset=True)

        if "project_role_id" in update_data:
            await self._validate_role(update_data["project_role_id"])
        if "assignment_status_id" in update_data:
            await self._validate_status(update_data["assignment_status_id"])
            update_data["status_id"] = update_data.pop("assignment_status_id")

        for field, value in update_data.items():
            setattr(assignment, field, value)

        assignment_id = assignment.id
        await self.db.commit()
        return await self._reload(assignment_id)

    async def delete(self, assignment: EmployeeProject) -> None:
        await self.db.delete(assignment)
        await self.db.commit()

    async def _validate_employee_not_fired(self, employee_id: uuid.UUID) -> None:
        result = await self.db.execute(select(Employee).where(Employee.id == employee_id))
        employee = result.scalar_one_or_none()
        if not employee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сотрудник не найден")
        if employee.status and employee.status.name == "Уволен":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя создать назначение для уволенного сотрудника",
            )

    async def _validate_project(self, project_id: uuid.UUID) -> None:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Проект не найден")
        if project.project_status and project.project_status.code in ("COMPLETED", "ARCHIVED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Нельзя создавать назначения для проекта со статусом «{project.project_status.name}»",
            )

    async def _validate_role(self, project_role_id: uuid.UUID) -> None:
        role = await self.db.get(ProjectRole, project_role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Проектная роль не найдена")

    async def _validate_status(self, status_id: uuid.UUID) -> None:
        s = await self.db.get(AssignmentStatus, status_id)
        if not s:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Статус назначения не найден")

    async def _reload(self, assignment_id: uuid.UUID) -> EmployeeProject:
        result = await self.db.execute(
            select(EmployeeProject)
            .options(
                selectinload(EmployeeProject.project).selectinload(Project.project_status),
                selectinload(EmployeeProject.project_role),
                selectinload(EmployeeProject.assignment_status),
            )
            .where(EmployeeProject.id == assignment_id)
        )
        return result.scalar_one()
