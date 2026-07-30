import asyncio
import json
import logging
import os
from typing import Any

from aiokafka import AIOKafkaConsumer

from src.kafka.topics import (
    DEPARTMENT_CREATED_TOPIC,
    DEPARTMENT_DELETED_TOPIC,
    DEPARTMENT_UPDATED_TOPIC,
    EMPLOYEE_PROFILE_CREATED_TOPIC,
    EMPLOYEE_UPDATED_TOPIC,
    ENTRY_CREATED_TOPIC,
    ENTRY_DELETED_TOPIC,
    ENTRY_UPDATED_TOPIC,
    PROJECT_CREATED_TOPIC,
    PROJECT_DELETED_TOPIC,
    PROJECT_UPDATED_TOPIC,
)
from src.kafka.handlers import (
    handle_department_deleted,
    handle_department_upsert,
    handle_employee_profile_created,
    handle_employee_updated,
    handle_entry_deleted,
    handle_entry_upsert,
    handle_project_deleted,
    handle_project_upsert,
)

logger = logging.getLogger(__name__)

HANDLERS = {
    "employee.profile_created": handle_employee_profile_created,
    "employee.updated": handle_employee_updated,
    "department.created": handle_department_upsert,
    "department.updated": handle_department_upsert,
    "department.deleted": handle_department_deleted,
    "project.created": handle_project_upsert,
    "project.updated": handle_project_upsert,
    "project.deleted": handle_project_deleted,
    "timesheet.entry_created": handle_entry_upsert,
    "timesheet.entry_updated": handle_entry_upsert,
    "timesheet.entry_deleted": handle_entry_deleted,
}

TOPICS = [
    EMPLOYEE_PROFILE_CREATED_TOPIC,
    EMPLOYEE_UPDATED_TOPIC,
    DEPARTMENT_CREATED_TOPIC,
    DEPARTMENT_UPDATED_TOPIC,
    DEPARTMENT_DELETED_TOPIC,
    PROJECT_CREATED_TOPIC,
    PROJECT_UPDATED_TOPIC,
    PROJECT_DELETED_TOPIC,
    ENTRY_CREATED_TOPIC,
    ENTRY_UPDATED_TOPIC,
    ENTRY_DELETED_TOPIC,
]


class KafkaEventConsumer:
    def __init__(self) -> None:
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
        self.group_id = os.getenv("KAFKA_GROUP_ID", "reporting-service")
        self._consumer: AIOKafkaConsumer | None = None
        self._running = False

    async def start(self) -> None:
        self._running = True
        while self._running:
            try:
                self._consumer = AIOKafkaConsumer(
                    *TOPICS,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=self.group_id,
                    enable_auto_commit=False,
                    auto_offset_reset="earliest",
                    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                )
                await self._consumer.start()
                logger.info("Kafka consumer started: %s", self.bootstrap_servers)
                async for message in self._consumer:
                    try:
                        await self._handle_message(message.value)
                        await self._consumer.commit()
                    except Exception:
                        logger.exception("Failed to process Kafka message: %s", message.value)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Kafka consumer failed, reconnecting in 5s...")
                await asyncio.sleep(5)
            finally:
                if self._consumer:
                    try:
                        await self._consumer.stop()
                    except Exception:
                        pass
                    self._consumer = None

    async def stop(self) -> None:
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            logger.info("Kafka consumer stopped")

    async def _handle_message(self, payload: dict[str, Any]) -> None:
        event_type = payload.get("event_type")
        handler = HANDLERS.get(event_type)
        if handler:
            await handler(payload)
        else:
            logger.debug("Unhandled event type: %s", event_type)
