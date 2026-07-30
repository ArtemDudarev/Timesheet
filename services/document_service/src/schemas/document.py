import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.models.document import DocumentStatus, StepRole, StepStatus


class DocumentTypeRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    color: str
    icon: Optional[str]
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class DocumentRouteStepCreate(BaseModel):
    employee_id: uuid.UUID
    role: StepRole
    step_order: int = Field(ge=1)


class DocumentRouteStepRead(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    step_order: int
    role: StepRole
    status: StepStatus
    acted_at: Optional[datetime]
    comment: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class DocumentRead(BaseModel):
    id: uuid.UUID
    title: str
    document_type: DocumentTypeRead
    author_id: uuid.UUID
    project_id: Optional[uuid.UUID]
    file_size: int
    status: DocumentStatus
    comment: Optional[str]
    route: list[DocumentRouteStepRead]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentReject(BaseModel):
    comment: str


class DocumentTemplateRead(BaseModel):
    id: uuid.UUID
    document_type: DocumentTypeRead
    title: str
    uploaded_by: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
