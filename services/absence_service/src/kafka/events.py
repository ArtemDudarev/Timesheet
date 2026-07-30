from src.kafka.producer import KafkaEventProducer
from src.kafka.topics import (
    ABSENCE_CREATED_TOPIC,
    ABSENCE_STATUS_CHANGED_TOPIC,
    ABSENCE_UPDATED_TOPIC,
)
from src.models.absence import Absence


def _absence_payload(event_type: str, absence: Absence) -> dict:
    return {
        "event_type": event_type,
        "absence_id": str(absence.id),
        "employee_id": str(absence.employee_id),
        "type_code": absence.absence_type.code if absence.absence_type else None,
        "date_from": absence.date_from.isoformat(),
        "date_to": absence.date_to.isoformat(),
        "status": absence.status.value,
    }


async def publish_absence_created(producer: KafkaEventProducer, absence: Absence) -> None:
    await producer.publish(
        ABSENCE_CREATED_TOPIC, _absence_payload("absence.created", absence)
    )


async def publish_absence_updated(producer: KafkaEventProducer, absence: Absence) -> None:
    await producer.publish(
        ABSENCE_UPDATED_TOPIC, _absence_payload("absence.updated", absence)
    )


async def publish_absence_status_changed(
    producer: KafkaEventProducer, absence: Absence
) -> None:
    await producer.publish(
        ABSENCE_STATUS_CHANGED_TOPIC, _absence_payload("absence.status_changed", absence)
    )
