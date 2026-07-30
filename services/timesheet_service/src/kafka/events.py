import uuid

from src.kafka.producer import KafkaEventProducer
from src.kafka.topics import (
    ENTRY_CREATED_TOPIC,
    ENTRY_DELETED_TOPIC,
    ENTRY_UPDATED_TOPIC,
    OVERTIME_CREATED_TOPIC,
    PERIOD_APPROVED_TOPIC,
    PERIOD_REJECTED_TOPIC,
    PERIOD_SUBMITTED_TOPIC,
)
from src.models.time_entry import TimeEntry
from src.models.timesheet_period import TimesheetPeriod


def _period_payload(event_type: str, period: TimesheetPeriod) -> dict:
    return {
        "event_type": event_type,
        "period_id": str(period.id),
        "employee_id": str(period.employee_id),
        "year": period.year,
        "month": period.month,
    }


async def publish_period_submitted(
    producer: KafkaEventProducer,
    period: TimesheetPeriod,
) -> None:
    await producer.publish(
        PERIOD_SUBMITTED_TOPIC,
        _period_payload("timesheet.period_submitted", period),
    )


async def publish_period_approved(
    producer: KafkaEventProducer,
    period: TimesheetPeriod,
) -> None:
    await producer.publish(
        PERIOD_APPROVED_TOPIC,
        _period_payload("timesheet.period_approved", period),
    )


async def publish_period_rejected(
    producer: KafkaEventProducer,
    period: TimesheetPeriod,
) -> None:
    payload = _period_payload("timesheet.period_rejected", period)
    payload["comment"] = period.rejection_comment
    await producer.publish(PERIOD_REJECTED_TOPIC, payload)


def _entry_payload(
    event_type: str,
    entry: TimeEntry,
    period: TimesheetPeriod,
    type_code: str | None,
    project_id: uuid.UUID | None,
) -> dict:
    return {
        "event_type": event_type,
        "entry_id": str(entry.id),
        "period_id": str(period.id),
        "employee_id": str(period.employee_id),
        "project_id": str(project_id) if project_id else None,
        "type_code": type_code,
        "date_from": entry.date_from.isoformat(),
        "date_to": entry.date_to.isoformat(),
        "spend_time": float(entry.spend_time) if entry.spend_time is not None else None,
        "year": period.year,
        "month": period.month,
    }


async def publish_entry_created(
    producer: KafkaEventProducer,
    entry: TimeEntry,
    period: TimesheetPeriod,
    type_code: str | None,
    project_id: uuid.UUID | None,
) -> None:
    await producer.publish(
        ENTRY_CREATED_TOPIC,
        _entry_payload("timesheet.entry_created", entry, period, type_code, project_id),
    )


async def publish_entry_updated(
    producer: KafkaEventProducer,
    entry: TimeEntry,
    period: TimesheetPeriod,
    type_code: str | None,
    project_id: uuid.UUID | None,
) -> None:
    await producer.publish(
        ENTRY_UPDATED_TOPIC,
        _entry_payload("timesheet.entry_updated", entry, period, type_code, project_id),
    )


async def publish_entry_deleted(
    producer: KafkaEventProducer,
    entry: TimeEntry,
    period: TimesheetPeriod,
    type_code: str | None,
    project_id: uuid.UUID | None,
) -> None:
    await producer.publish(
        ENTRY_DELETED_TOPIC,
        _entry_payload("timesheet.entry_deleted", entry, period, type_code, project_id),
    )


async def publish_overtime_created(
    producer: KafkaEventProducer,
    entry: TimeEntry,
    employee_id: uuid.UUID,
) -> None:
    await producer.publish(
        OVERTIME_CREATED_TOPIC,
        {
            "event_type": "timesheet.overtime_created",
            "employee_id": str(employee_id),
            "time_entry_id": str(entry.id),
            "date_from": entry.date_from.isoformat(),
            "date_to": entry.date_to.isoformat(),
            "spend_time": float(entry.spend_time),
        },
    )
