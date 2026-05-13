import uuid
from pydantic import BaseModel

class ProjectBase(BaseModel):
    project_name: str
    project_status: str

class ProjectCreate(ProjectBase):
    pass

class ProjectRead(ProjectBase):
    id: uuid.UUID

    class Config:
        from_attributes = True

class ProjectUpdate(BaseModel):
    project_name: str | None = None
    project_status: str | None = None