"""Разовый бэкфилл: публикует timesheet.entry_created для всех существующих записей табеля.

Нужен, потому что записи, созданные до появления entry-топиков, не имеют событий —
без бэкфилла реплика reporting_service их никогда не увидит.

Запуск (внутри контейнера):
    docker exec timesheet-timesheet_service-1 python -m src.backfill_entry_events

Повторный запуск безопасен: консюмеры упсертят по entry_id.
"""
import asyncio
import logging

from sqlalchemy import select

from src.database import async_session_maker
from src.kafka.events import publish_entry_created
from src.kafka.producer import KafkaEventProducer

# Полный набор моделей — иначе SQLAlchemy не сконфигурирует мапперы связей
from src.models.user import User  # noqa: F401
from src.models.role import Role  # noqa: F401
from src.models.user_role import user_role  # noqa: F401
from src.models.employee import Employee  # noqa: F401
from src.models.project import Project  # noqa: F401
from src.models.project_role import ProjectRole  # noqa: F401
from src.models.overtime_approval import OvertimeApproval  # noqa: F401
from src.models.production_calendar import ProductionCalendar  # noqa: F401
from src.models.employee_project import Assignment
from src.models.entry_type_ref import EntryTypeRef
from src.models.time_entry import TimeEntry
from src.models.timesheet_period import TimesheetPeriod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    producer = KafkaEventProducer()
    await producer.start()
    published = 0
    try:
        async with async_session_maker() as session:
            types_result = await session.execute(select(EntryTypeRef))
            type_codes = {t.id: t.code for t in types_result.scalars().all()}

            assignments_result = await session.execute(select(Assignment))
            assignment_projects = {a.id: a.project_id for a in assignments_result.scalars().all()}

            periods_result = await session.execute(select(TimesheetPeriod))
            periods = {p.id: p for p in periods_result.scalars().all()}

            entries_result = await session.execute(select(TimeEntry))
            for entry in entries_result.scalars().all():
                period = periods.get(entry.timesheet_period_id)
                if period is None:
                    logger.warning("Пропуск entry %s: период не найден", entry.id)
                    continue
                await publish_entry_created(
                    producer,
                    entry,
                    period,
                    type_codes.get(entry.type_id),
                    assignment_projects.get(entry.assignment_id) if entry.assignment_id else None,
                )
                published += 1
    finally:
        await producer.stop()
    logger.info("Бэкфилл завершён: опубликовано %d событий", published)


if __name__ == "__main__":
    asyncio.run(main())
