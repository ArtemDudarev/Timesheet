import asyncio
import json
import logging
import os
from typing import Any

from aiokafka import AIOKafkaConsumer

from src.kafka.topics import (
    EMPLOYEE_PROFILE_CREATED_TOPIC,
    EMPLOYEE_UPDATED_TOPIC,
    EMPLOYEE_PROJECT_ASSIGNED_TOPIC,
    EMPLOYEE_ROLE_ASSIGNED_TOPIC,
    PROJECT_CREATED_TOPIC,
    PROJECT_DELETED_TOPIC,
    PROJECT_ROLE_CREATED_TOPIC,
    PROJECT_ROLE_DELETED_TOPIC,
    PROJECT_ROLE_UPDATED_TOPIC,
    PROJECT_UPDATED_TOPIC,
    ROLE_CREATED_TOPIC,
    ROLE_DELETED_TOPIC,
    ROLE_UPDATED_TOPIC,
    USER_CREATED_TOPIC,
)
from src.kafka.handlers import (
    handle_employee_profile_created,
    handle_employee_updated,
    handle_employee_project_assigned,
    handle_employee_role_assigned,
    handle_project_created,
    handle_project_deleted,
    handle_project_role_created,
    handle_project_role_deleted,
    handle_project_role_updated,
    handle_project_updated,
    handle_role_created,
    handle_role_deleted,
    handle_role_updated,
    handle_user_created,
)

logger = logging.getLogger(__name__)

HANDLERS = {
    "user.created": handle_user_created,
    "employee.profile_created": handle_employee_profile_created,
    "employee.updated": handle_employee_updated,
    "employee.role_assigned": handle_employee_role_assigned,
    "employee.project_assigned": handle_employee_project_assigned,
    "project.created": handle_project_created,
    "project.updated": handle_project_updated,
    "project.deleted": handle_project_deleted,
    "project_role.created": handle_project_role_created,
    "project_role.updated": handle_project_role_updated,
    "project_role.deleted": handle_project_role_deleted,
    "role.created": handle_role_created,
    "role.updated": handle_role_updated,
    "role.deleted": handle_role_deleted,
}

TOPICS = [
    USER_CREATED_TOPIC,
    EMPLOYEE_PROFILE_CREATED_TOPIC,
    EMPLOYEE_UPDATED_TOPIC,
    EMPLOYEE_ROLE_ASSIGNED_TOPIC,
    EMPLOYEE_PROJECT_ASSIGNED_TOPIC,
    PROJECT_CREATED_TOPIC,
    PROJECT_UPDATED_TOPIC,
    PROJECT_DELETED_TOPIC,
    PROJECT_ROLE_CREATED_TOPIC,
    PROJECT_ROLE_UPDATED_TOPIC,
    PROJECT_ROLE_DELETED_TOPIC,
    ROLE_CREATED_TOPIC,
    ROLE_UPDATED_TOPIC,
    ROLE_DELETED_TOPIC,
]


class KafkaEventConsumer:
    def __init__(self, producer=None) -> None:
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
        self.group_id = os.getenv("KAFKA_GROUP_ID", "timesheet-service")
        self._consumer: AIOKafkaConsumer | None = None
        self._producer = producer
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
            await handler(payload, self._producer)
        else:
            logger.debug("Unhandled event type: %s", event_type)
