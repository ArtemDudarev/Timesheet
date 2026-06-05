import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AssignmentStatusResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)
