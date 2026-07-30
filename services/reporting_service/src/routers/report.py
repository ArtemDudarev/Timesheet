from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.dependencies import require_permission
from src.schemas.report import PlanFactRow, ProjectStatRow, ReportsSummary, UtilizationRow
from src.services.export_service import EXPORT_TYPES, build_xlsx
from src.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])

_reader = Depends(require_permission("report:read"))

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/utilization", response_model=list[UtilizationRow])
async def utilization(
    period: str,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _reader,
):
    return await ReportService(session).utilization(period)


@router.get("/projects", response_model=list[ProjectStatRow])
async def projects(
    period: str,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _reader,
):
    return await ReportService(session).projects(period)


@router.get("/plan-fact", response_model=list[PlanFactRow])
async def plan_fact(
    period: str,
    group_by: str = "department",
    session: AsyncSession = Depends(get_async_session),
    _: dict = _reader,
):
    if group_by != "department":
        raise HTTPException(status_code=422, detail="Поддерживается только group_by=department")
    return await ReportService(session).plan_fact(period)


@router.get("/summary", response_model=ReportsSummary)
async def summary(
    period: str,
    session: AsyncSession = Depends(get_async_session),
    _: dict = _reader,
):
    return await ReportService(session).summary(period)


@router.get("/export")
async def export(
    type: str,
    period: str,
    format: str = "xlsx",
    session: AsyncSession = Depends(get_async_session),
    _: dict = _reader,
):
    if format != "xlsx":
        raise HTTPException(status_code=422, detail="Поддерживается только format=xlsx")
    if type not in EXPORT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"type должен быть одним из: {', '.join(EXPORT_TYPES)}",
        )

    svc = ReportService(session)
    if type == "utilization":
        rows = await svc.utilization(period)
    elif type == "projects":
        rows = await svc.projects(period)
    else:
        rows = await svc.plan_fact(period)

    buffer = build_xlsx(type, period, rows)
    filename = f"report_{type}_{period}.xlsx"
    return StreamingResponse(
        buffer,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
