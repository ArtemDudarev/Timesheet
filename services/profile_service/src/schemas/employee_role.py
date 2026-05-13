from pydantic import BaseModel


class EmployeeRoleRead(BaseModel):
    employee_role_id: int
    employee_role_employee_id: int
    employee_role_role_id: int

    class Config:
        from_attributes = True
