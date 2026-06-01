import uuid
from typing import Optional

from pydantic import BaseModel


class EntryTypeRefResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: Optional[str]

    model_config = {"from_attributes": True}
