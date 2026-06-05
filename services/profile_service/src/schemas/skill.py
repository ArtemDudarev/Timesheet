import uuid
from typing import List

from pydantic import BaseModel, ConfigDict


class SkillRead(BaseModel):
    id: uuid.UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class SkillCreate(BaseModel):
    name: str


class SkillsUpdate(BaseModel):
    skill_ids: List[uuid.UUID]
