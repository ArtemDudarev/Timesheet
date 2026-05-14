import uuid

from pydantic import BaseModel


class RoleRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None

    class Config:
        from_attributes = True
