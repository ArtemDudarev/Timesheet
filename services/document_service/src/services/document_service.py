import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.document import (
    Document,
    DocumentRouteStep,
    DocumentStatus,
    DocumentTemplate,
    StepStatus,
)
from src.models.document_type import DocumentType
from src.models.employee import Employee
from src.schemas.document import DocumentRouteStepCreate

DOCUMENT_FILTERS = ("all", "pending", "mine", "signed")


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        caller_id: uuid.UUID,
        read_any: bool,
        filter_: str = "all",
        project_id: uuid.UUID | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Document]:
        q = select(Document)
        if not read_any:
            # Автор или участник маршрута
            participant_sq = (
                select(DocumentRouteStep.document_id)
                .where(DocumentRouteStep.employee_id == caller_id)
                .subquery()
            )
            q = q.where(
                or_(Document.author_id == caller_id, Document.id.in_(select(participant_sq)))
            )

        if filter_ == "mine":
            q = q.where(Document.author_id == caller_id)
        elif filter_ == "signed":
            q = q.where(Document.status == DocumentStatus.SIGNED)
        elif filter_ == "pending":
            # Ждут действия вызывающего: его шаг — текущий (минимальный PENDING)
            q = q.where(Document.status == DocumentStatus.PENDING)

        if project_id:
            q = q.where(Document.project_id == project_id)
        if search:
            q = q.where(Document.title.ilike(f"%{search}%"))

        q = q.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        documents = list(result.scalars().all())

        if filter_ == "pending":
            documents = [
                d for d in documents
                if (step := self.current_step(d)) is not None
                and step.employee_id == caller_id
            ]
        return documents

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        return await self.db.get(Document, document_id)

    def can_read(self, document: Document, caller_id: uuid.UUID, read_any: bool) -> bool:
        if read_any or document.author_id == caller_id:
            return True
        return any(step.employee_id == caller_id for step in document.route)

    @staticmethod
    def current_step(document: Document) -> DocumentRouteStep | None:
        pending = [s for s in document.route if s.status == StepStatus.PENDING]
        return min(pending, key=lambda s: s.step_order) if pending else None

    async def create(
        self,
        author_id: uuid.UUID,
        title: str,
        type_id: uuid.UUID,
        file_key: str,
        file_size: int,
        route: list[DocumentRouteStepCreate],
        project_id: uuid.UUID | None = None,
        comment: str | None = None,
    ) -> Document:
        if not route:
            raise HTTPException(status_code=422, detail="Маршрут подписания не может быть пустым")
        doc_type = await self.db.get(DocumentType, type_id)
        if doc_type is None:
            raise HTTPException(status_code=404, detail="Тип документа не найден")
        for step in route:
            employee = await self.db.get(Employee, step.employee_id)
            if employee is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Участник маршрута {step.employee_id} не найден",
                )

        document = Document(
            title=title,
            type_id=type_id,
            author_id=author_id,
            project_id=project_id,
            file_key=file_key,
            file_size=file_size,
            comment=comment,
            status=DocumentStatus.PENDING,
            route=[
                DocumentRouteStep(
                    employee_id=step.employee_id,
                    role=step.role,
                    step_order=step.step_order,
                )
                for step in route
            ],
        )
        self.db.add(document)
        await self.db.flush()
        await self.db.refresh(document, attribute_names=["document_type", "route"])
        return document

    async def sign(self, document: Document, caller_id: uuid.UUID) -> Document:
        step = self._assert_current_step_caller(document, caller_id)
        step.status = StepStatus.SIGNED
        step.acted_at = datetime.utcnow()
        if self.current_step(document) is None:  # последний шаг
            document.status = DocumentStatus.SIGNED
        await self.db.flush()
        return document

    async def reject(self, document: Document, caller_id: uuid.UUID, comment: str) -> Document:
        step = self._assert_current_step_caller(document, caller_id)
        step.status = StepStatus.REJECTED
        step.acted_at = datetime.utcnow()
        step.comment = comment
        document.status = DocumentStatus.REJECTED  # маршрут прерывается
        await self.db.flush()
        return document

    def _assert_current_step_caller(
        self, document: Document, caller_id: uuid.UUID
    ) -> DocumentRouteStep:
        if document.status != DocumentStatus.PENDING:
            raise HTTPException(status_code=409, detail="Документ уже обработан")
        step = self.current_step(document)
        if step is None:
            raise HTTPException(status_code=409, detail="Маршрут документа завершён")
        if step.employee_id != caller_id:
            raise HTTPException(
                status_code=403, detail="Сейчас не ваш шаг маршрута подписания"
            )
        return step

    # ── Шаблоны ───────────────────────────────────────────────────────────────

    async def get_templates(self) -> list[DocumentTemplate]:
        result = await self.db.execute(
            select(DocumentTemplate).order_by(DocumentTemplate.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_template(
        self, type_id: uuid.UUID, title: str, file_key: str, uploaded_by: uuid.UUID
    ) -> DocumentTemplate:
        doc_type = await self.db.get(DocumentType, type_id)
        if doc_type is None:
            raise HTTPException(status_code=404, detail="Тип документа не найден")
        template = DocumentTemplate(
            type_id=type_id, title=title, file_key=file_key, uploaded_by=uploaded_by
        )
        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template, attribute_names=["document_type"])
        return template

    async def delete_template(self, template_id: uuid.UUID) -> DocumentTemplate:
        template = await self.db.get(DocumentTemplate, template_id)
        if template is None:
            raise HTTPException(status_code=404, detail="Шаблон не найден")
        await self.db.delete(template)
        await self.db.flush()
        return template

    async def get_types(self) -> list[DocumentType]:
        result = await self.db.execute(select(DocumentType).order_by(DocumentType.name))
        return list(result.scalars().all())
