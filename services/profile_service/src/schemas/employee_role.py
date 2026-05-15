import uuid
from pydantic import BaseModel, ConfigDict

class EmployeeRoleRead(BaseModel):
    employee_id: uuid.UUID
    role_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)