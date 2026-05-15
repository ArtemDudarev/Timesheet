import uuid
from pydantic import BaseModel, ConfigDict

class RoleBase(BaseModel):
    name: str
    description: str | None = None

class RoleRead(RoleBase):
    id: uuid.UUID
    
    model_config = ConfigDict(from_attributes=True)