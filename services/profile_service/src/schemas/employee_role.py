import uuid

from pydantic import BaseModel


class EmployeeRoleRead(BaseModel):
    employee_id: uuid.UUID
    role_id: uuid.UUID

    class Config:
        from_attributes = True
