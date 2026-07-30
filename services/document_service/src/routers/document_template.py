import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import get_current_user, require_permission
from src.schemas.document import DocumentTemplateRead, DocumentTypeRead
from src.services.document_service import DocumentService
from src.storage import storage

router = APIRouter(tags=["Document Templates"])

_template_manager = Depends(require_permission("document:manage_templates"))


@router.get("/document-types/", response_model=list[DocumentTypeRead])
async def get_document_types(
    session: AsyncSession = Depends(get_async_session),
    _: dict = Depends(get_current_user),
):
    return await DocumentService(session).get_types()


@router.get("/document-templates/", response_model=list[DocumentTemplateRead])
async def get_templates(
    session: AsyncSession = Depends(get_async_session),
    _: dict = Depends(get_current_user),
):
    return await DocumentService(session).get_templates()


@router.post(
    "/document-templates/",
    response_model=DocumentTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    file: UploadFile,
    title: str = Form(...),
    type_id: uuid.UUID = Form(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = _template_manager,
):
    file_key, _ = storage.save(file.file, file.filename or "file")
    try:
        template = await DocumentService(session).create_template(
            type_id=type_id,
            title=title,
            file_key=file_key,
            uploaded_by=uuid.UUID(current_user["sub"]),
        )
        await session.commit()
        return template
    except Exception:
        storage.delete(file_key)
        raise


@router.get("/document-templates/{template_id}/file")
async def download_template_file(
    template_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    _: dict = Depends(get_current_user),
):
    svc = DocumentService(session)
    templates = {t.id: t for t in await svc.get_templates()}
    template = templates.get(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    try:
        stream = storage.open(template.file_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Файл не найден в хранилище")
    return StreamingResponse(
        stream,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{template.file_key}"'},
    )


@router.delete("/document-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _template_manager,
):
    template = await DocumentService(session).delete_template(template_id)
    storage.delete(template.file_key)
    await session.commit()
