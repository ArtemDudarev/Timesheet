import uuid
from datetime import date as real_date
from decimal import Decimal
from unittest.mock import patch

import pytest

from src.models.employee_project import Assignment
from src.models.entry_type_ref import EntryTypeRef
from src.models.project import Project
from src.models.project_role import ProjectRole
from src.models.time_entry import TimeEntry
from src.models.timesheet_period import TimesheetPeriod
from src.services.summary_service import SummaryService
from tests.conftest import EMPLOYEE_ID


class _FixedDate(real_date):
    """Подменяет date.today() внутри summary_service, сохраняя конструктор date(...)."""

    _fixed: real_date

    @classmethod
    def today(cls):
        return cls._fixed


def _frozen(year: int, month: int, day: int):
    frozen = type("_Frozen", (_FixedDate,), {"_fixed": real_date(year, month, day)})
    return patch("src.services.summary_service.date", frozen)


async def test_utilization_uses_elapsed_norm_for_current_month(db_session, test_period):
    """1 июня отработано 8ч — вся норма 'на сегодня' — должно быть 100%, а не 8/176 ≈ 4.5%."""
    service = SummaryService(db_session)
    service._sum_entries = lambda entries: Decimal("8")

    with _frozen(2026, 6, 1):
        summary = await service.get_summary(EMPLOYEE_ID, 2026, 6)

    assert summary.utilization_pct == 100.0
    assert summary.norm_hours == Decimal("176")  # полная норма месяца не меняется


async def test_utilization_uses_full_norm_for_past_month(db_session, test_period):
    """Для уже завершённого месяца утилизация — от полной месячной нормы, как раньше."""
    service = SummaryService(db_session)
    service._sum_entries = lambda entries: Decimal("88")

    with _frozen(2026, 7, 15):
        summary = await service.get_summary(EMPLOYEE_ID, 2026, 6)

    assert summary.utilization_pct == round(88 / 176 * 100, 1)


async def test_active_projects_count_uses_project_status_code(db_session, test_period):
    """active_projects_count считает по КОДУ статуса самого ПРОЕКТА (project.status_code),
    а не по статусу назначения сотрудника: сотрудник может быть активно привлечён
    (assignment ACTIVE) к проекту, который сам ещё в статусе 'Планируется' — такой
    проект в 'активные' попадать не должен. Заодно event.status_code раньше не
    приходил вообще (management_service слал только .name — 'Активный'/'Планируется'),
    с которым 'ACTIVE' никогда не совпадало."""
    role = ProjectRole(id=uuid.uuid4(), name="Разработчик")
    db_session.add(role)
    active_project = Project(id=uuid.uuid4(), name="Активный проект", status_code="ACTIVE")
    planned_project = Project(id=uuid.uuid4(), name="Проект в планах", status_code="PLANNED")
    completed_project = Project(id=uuid.uuid4(), name="Завершённый проект", status_code="COMPLETED")
    db_session.add_all([active_project, planned_project, completed_project])
    await db_session.flush()

    db_session.add_all([
        # Назначение "ACTIVE" на проект, который сам ещё не стартовал — не должен считаться
        Assignment(id=uuid.uuid4(), employee_id=EMPLOYEE_ID, project_id=planned_project.id,
                   project_role_id=role.id, status="ACTIVE"),
        Assignment(id=uuid.uuid4(), employee_id=EMPLOYEE_ID, project_id=active_project.id,
                   project_role_id=role.id, status="ACTIVE"),
        Assignment(id=uuid.uuid4(), employee_id=EMPLOYEE_ID, project_id=completed_project.id,
                   project_role_id=role.id, status="REMOVED"),
    ])
    await db_session.flush()

    service = SummaryService(db_session)
    with _frozen(2026, 6, 1):
        summary = await service.get_summary(EMPLOYEE_ID, 2026, 6)

    assert summary.active_projects_count == 1
    assert summary.total_projects_count == 3


async def test_prev_month_utilization_compares_to_two_months_ago(db_session, test_employee):
    """'Утилизация' в статистике профиля — отдельная метрика от 'Загрузки' (utilization_pct):
    всегда за прошлый ЗАВЕРШЁННЫЙ месяц (без шума неполного текущего), тренд — относительно
    позапрошлого. Смотрим на июль 2026 → 'Утилизация' должна показывать июнь (50%),
    тренд — июнь минус май (50% - 80% = -30)."""
    entry_type = EntryTypeRef(id=uuid.uuid4(), code="WORK", name="Работа")
    db_session.add(entry_type)
    # Текущий (июльский) период тоже создаём заранее — иначе get_or_create() создаст его
    # "на лету" без выборки, и .entries останется незагруженным (selectin грузится SELECT'ом)
    july_period = TimesheetPeriod(id=uuid.uuid4(), employee_id=EMPLOYEE_ID, year=2026, month=7)
    june_period = TimesheetPeriod(id=uuid.uuid4(), employee_id=EMPLOYEE_ID, year=2026, month=6)
    may_period = TimesheetPeriod(id=uuid.uuid4(), employee_id=EMPLOYEE_ID, year=2026, month=5)
    db_session.add_all([july_period, june_period, may_period])
    await db_session.flush()

    service = SummaryService(db_session)
    june_norm = await service._calc_norm(2026, 6)
    may_norm = await service._calc_norm(2026, 5)

    db_session.add_all([
        TimeEntry(id=uuid.uuid4(), timesheet_period_id=june_period.id, employee_id=EMPLOYEE_ID,
                  type_id=entry_type.id, date_from=real_date(2026, 6, 2), date_to=real_date(2026, 6, 2),
                  spend_time=june_norm / 2),
        TimeEntry(id=uuid.uuid4(), timesheet_period_id=may_period.id, employee_id=EMPLOYEE_ID,
                  type_id=entry_type.id, date_from=real_date(2026, 5, 4), date_to=real_date(2026, 5, 4),
                  spend_time=may_norm * Decimal("0.8")),
    ])
    await db_session.flush()

    with _frozen(2026, 7, 9):
        summary = await service.get_summary(EMPLOYEE_ID, 2026, 7)

    assert summary.prev_month_utilization_pct == pytest.approx(50.0, abs=0.1)
    assert summary.utilization_delta == pytest.approx(-30.0, abs=0.1)
