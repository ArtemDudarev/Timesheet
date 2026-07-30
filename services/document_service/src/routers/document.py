import json
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user
from src.kafka.events import publish_document_route_updated
from src.models.document import Document
from src.schemas.document import DocumentRead, DocumentReject, DocumentRouteStepCreate
from src.services.document_service import DOCUMENT_FILTERS, DocumentService
from src.storage import storage

router = APIRouter(prefix="/documents", tags=["Documents"])


def _read_any(current_user: dict) -> bool:
    return "document:read_any" in current_user.get("permissions", [])


async def _get_readable_document(
    document_id: uuid.UUID, session: AsyncSession, current_user: dict
) -> Document:
    svc = DocumentService(session)
    document = await svc.get_by_id(document_id)
    # Недоступный документ неотличим от несуществующего
    if not document or not svc.can_read(
        document, uuid.UUID(current_user["sub"]), _read_any(current_user)
    ):
        raise HTTPException(status_code=404, detail="Документ не найден")
    return document


@router.get("/", response_model=list[DocumentRead])
async def get_documents(
    filter: str = Query("all"),
    project_id: uuid.UUID | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    if filter not in DOCUMENT_FILTERS:
        raise HTTPException(
            status_code=422, detail=f"filter должен быть одним из: {', '.join(DOCUMENT_FILTERS)}"
        )
    return await DocumentService(session).get_all(
        caller_id=uuid.UUID(current_user["sub"]),
        read_any=_read_any(current_user),
        filter_=filter,
        project_id=project_id,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    return await _get_readable_document(document_id, session, current_user)


@router.post("/", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def create_document(
    request: Request,
    file: UploadFile,
    title: str = Form(...),
    type_id: uuid.UUID = Form(...),
    route: str = Form(..., description='JSON-массив шагов: [{"employee_id", "role", "step_order"}]'),
    project_id: uuid.UUID | None = Form(None),
    comment: str | None = Form(None),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    try:
        route_steps = [DocumentRouteStepCreate(**s) for s in json.loads(route)]
    except (json.JSONDecodeError, TypeError, ValidationError):
        raise HTTPException(status_code=422, detail="route должен быть JSON-массивом шагов маршрута")

    file_key, file_size = storage.save(file.file, file.filename or "file")
    try:
        document = await DocumentService(session).create(
            author_id=uuid.UUID(current_user["sub"]),
            title=title,
            type_id=type_id,
            file_key=file_key,
            file_size=file_size,
            route=route_steps,
            project_id=project_id,
            comment=comment,
        )
        await publish_document_route_updated(request.app.state.kafka_producer, document)
        await session.commit()
        return document
    except Exception:
        storage.delete(file_key)  # не оставляем осиротевший файл
        raise


@router.post("/{document_id}/sign", response_model=DocumentRead)
async def sign_document(
    document_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    document = await _get_readable_document(document_id, session, current_user)
    document = await DocumentService(session).sign(document, uuid.UUID(current_user["sub"]))
    await publish_document_route_updated(request.app.state.kafka_producer, document)
    await session.commit()
    return document


@router.post("/{document_id}/reject", response_model=DocumentRead)
async def reject_document(
    document_id: uuid.UUID,
    data: DocumentReject,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    document = await _get_readable_document(document_id, session, current_user)
    document = await DocumentService(session).reject(
        document, uuid.UUID(current_user["sub"]), data.comment
    )
    await publish_document_route_updated(request.app.state.kafka_producer, document)
    await session.commit()
    return document


@router.get("/{document_id}/file")
async def download_document_file(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    document = await _get_readable_document(document_id, session, current_user)
    try:
        stream = storage.open(document.file_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Файл не найден в хранилище")
    return StreamingResponse(
        stream,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{document.file_key}"'},
    )
