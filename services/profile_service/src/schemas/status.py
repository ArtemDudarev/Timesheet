from pydantic import BaseModel, ConfigDict

class StatusBase(BaseModel):
    status_name: str
    status_description: str | None = None

class StatusCreate(StatusBase):
    pass

class StatusRead(StatusBase):
    status_id: int
    
    model_config = ConfigDict(from_attributes=True)