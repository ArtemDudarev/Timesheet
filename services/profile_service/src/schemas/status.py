import uuid
from pydantic import BaseModel, ConfigDict


class StatusRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)