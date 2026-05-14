import uuid
from pydantic import BaseModel, ConfigDict

class StatusBase(BaseModel):
    status_name: str
    status_description: str | None = None

class StatusCreate(StatusBase):
    pass

class StatusRead(StatusBase):
    # Теперь здесь UUID
    status_id: uuid.UUID
    
    model_config = ConfigDict(from_attributes=True)