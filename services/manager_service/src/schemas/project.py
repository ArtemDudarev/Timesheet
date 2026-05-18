import uuid
from pydantic import BaseModel, ConfigDict

class ProjectBase(BaseModel):
    name: str
    status: str

class ProjectCreate(ProjectBase):
    pass

class ProjectRead(ProjectBase):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)

class ProjectUpdate(BaseModel):
    name: str | None = None
    status: str | None = None