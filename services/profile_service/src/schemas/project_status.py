import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProjectStatusResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
