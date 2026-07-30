import uuid
from decimal import Decimal

from sqlalchemy import Integer, Numeric, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DepartmentPlan(Base):
    """Плановые часы отдела на месяц — собственная сущность reporting_service."""

    __tablename__ = "department_plan"
    __table_args__ = (
        UniqueConstraint("department_id", "year", "month", name="uq_plan_department_year_month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    department_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
