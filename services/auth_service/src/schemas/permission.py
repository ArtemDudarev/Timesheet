import uuid

from pydantic import BaseModel, ConfigDict


class PermissionRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RoleWithPermissionsRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    permissions: list[PermissionRead] = []

    model_config = ConfigDict(from_attributes=True)


class RolePermissionsUpdate(BaseModel):
    permission_codes: list[str]
