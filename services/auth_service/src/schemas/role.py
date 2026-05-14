import uuid
from pydantic import BaseModel

class RoleBase(BaseModel):
    name: str
    description: str | None = None

class RoleRead(RoleBase):
    id: uuid.UUID # Изменено на uuid.UUID
    
    class Config:
        from_attributes = True