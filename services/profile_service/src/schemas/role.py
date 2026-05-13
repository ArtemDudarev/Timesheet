from pydantic import BaseModel


class RoleRead(BaseModel):
    role_id: int
    role_name: str
    role_description: str | None = None

    class Config:
        from_attributes = True
