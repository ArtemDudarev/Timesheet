import asyncio
import json
import logging
import os
from typing import Any

from aiokafka import AIOKafkaConsumer

from src.kafka.topics import (
    ABSENCE_STATUS_CHANGED_TOPIC,
    DOCUMENT_ROUTE_UPDATED_TOPIC,
    EMPLOYEE_PROFILE_CREATED_TOPIC,
    EMPLOYEE_ROLE_ASSIGNED_TOPIC,
    EMPLOYEE_UPDATED_TOPIC,
    OVERTIME_CREATED_TOPIC,
    PASSWORD_RESET_REQUESTED_TOPIC,
    PERIOD_APPROVED_TOPIC,
    PERIOD_REJECTED_TOPIC,
    PERIOD_SUBMITTED_TOPIC,
    ROLE_CREATED_TOPIC,
    ROLE_DELETED_TOPIC,
    ROLE_UPDATED_TOPIC,
    USER_CREATED_TOPIC,
)
from src.kafka.handlers import (
    handle_absence_status_changed,
    handle_document_route_updated,
    handle_employee_profile_created,
    handle_employee_role_assigned,
    handle_employee_updated,
    handle_overtime_created,
    handle_password_reset_requested,
    handle_period_approved,
    handle_period_rejected,
    handle_period_submitted,
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
    "role.created": handle_role_created,
    "role.updated": handle_role_updated,
    "role.deleted": handle_role_deleted,
    "timesheet.period_submitted": handle_period_submitted,
    "timesheet.period_approved": handle_period_approved,
    "timesheet.period_rejected": handle_period_rejected,
    "timesheet.overtime_created": handle_overtime_created,
    "password_reset.requested": handle_password_reset_requested,
    "absence.status_changed": handle_absence_status_changed,
    "document.route_updated": handle_document_route_updated,
}

TOPICS = [
    USER_CREATED_TOPIC,
    EMPLOYEE_PROFILE_CREATED_TOPIC,
    EMPLOYEE_UPDATED_TOPIC,
    EMPLOYEE_ROLE_ASSIGNED_TOPIC,
    ROLE_CREATED_TOPIC,
    ROLE_UPDATED_TOPIC,
    ROLE_DELETED_TOPIC,
    PERIOD_SUBMITTED_TOPIC,
    PERIOD_APPROVED_TOPIC,
    PERIOD_REJECTED_TOPIC,
    OVERTIME_CREATED_TOPIC,
    PASSWORD_RESET_REQUESTED_TOPIC,
    ABSENCE_STATUS_CHANGED_TOPIC,
    DOCUMENT_ROUTE_UPDATED_TOPIC,
]


class KafkaEventConsumer:
    def __init__(self) -> None:
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
        self.group_id = os.getenv("KAFKA_GROUP_ID", "notification-service")
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
