import uuid

from src.kafka.producer import KafkaEventProducer
from src.kafka.topics import OVERTIME_CREATED_TOPIC
from src.models.time_entry import TimeEntry


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
