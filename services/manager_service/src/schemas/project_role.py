from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProjectRoleCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectRoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProjectRoleResponse(ProjectRoleCreate):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
