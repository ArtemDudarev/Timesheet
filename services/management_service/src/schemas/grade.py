import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class GradeRead(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    sort_order: int = 0

    model_config = ConfigDict(from_attributes=True)


class GradeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sort_order: int = 0


class GradeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
