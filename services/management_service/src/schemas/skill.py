import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SkillRead(BaseModel):
    id: uuid.UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class SkillCreate(BaseModel):
    name: str


class SkillUpdate(BaseModel):
    name: Optional[str] = None
