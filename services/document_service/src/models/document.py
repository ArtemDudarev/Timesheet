import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class DocumentStatus(str, enum.Enum):
    DRAFT = "Черновик"
    PENDING = "На подписании"
    SIGNED = "Подписан"
    REJECTED = "Отклонён"


class StepRole(str, enum.Enum):
    # Английские коды: клиент передаёт их в теле запроса (контракт), как NotificationType
    SIGNER = "SIGNER"
    APPROVER = "APPROVER"


class StepStatus(str, enum.Enum):
    PENDING = "Ожидает"
    SIGNED = "Подписано"
    REJECTED = "Отклонено"


class Document(Base):
    __tablename__ = "document"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("document_type.id"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)
    file_key: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"),
        nullable=False,
        default=DocumentStatus.PENDING,
    )
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    document_type: Mapped["DocumentType"] = relationship("DocumentType", lazy="selectin")
    route: Mapped[list["DocumentRouteStep"]] = relationship(
        "DocumentRouteStep",
        back_populates="document",
        lazy="selectin",
        order_by="DocumentRouteStep.step_order",
        cascade="all, delete-orphan",
    )


class DocumentRouteStep(Base):
    __tablename__ = "document_route_step"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("document.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[StepRole] = mapped_column(
        Enum(StepRole, name="step_role"), nullable=False
    )
    status: Mapped[StepStatus] = mapped_column(
        Enum(StepStatus, name="step_status"),
        nullable=False,
        default=StepStatus.PENDING,
    )
    acted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="route")


class DocumentTemplate(Base):
    __tablename__ = "document_template"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    type_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("document_type.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_key: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    document_type: Mapped["DocumentType"] = relationship("DocumentType", lazy="selectin")
