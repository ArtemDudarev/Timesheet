from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProjectRoleResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
