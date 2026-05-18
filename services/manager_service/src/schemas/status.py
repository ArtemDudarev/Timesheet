import uuid
from pydantic import BaseModel, ConfigDict

class StatusBase(BaseModel):
    name: str
    description: str | None = None

class StatusCreate(StatusBase):
    pass

class StatusRead(StatusBase):
    id: uuid.UUID
    
    model_config = ConfigDict(from_attributes=True)