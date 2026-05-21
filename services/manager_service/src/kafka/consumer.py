import asyncio
import json
import logging
import os
from typing import Any

from aiokafka import AIOKafkaConsumer

from src.kafka.topics import (
    EMPLOYEE_CREATED_TOPIC,
    EMPLOYEE_UPDATED_TOPIC,
)
from src.kafka.handlers import (
    handle_employee_created,
    handle_employee_updated,
)

logger = logging.getLogger(__name__)

HANDLERS = {
    "employee.created": handle_employee_created,
    "employee.updated": handle_employee_updated,
}

TOPICS = [
    EMPLOYEE_CREATED_TOPIC,
    EMPLOYEE_UPDATED_TOPIC,
]


class KafkaEventConsumer:
    def __init__(self) -> None:
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
        self.group_id = os.getenv("KAFKA_GROUP_ID", "manager-service")
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
                    value_deserializer=lambda value: json.loads(value.decode("utf-8")),
                )
                await self._consumer.start()
                logger.info("Kafka consumer started: %s", self.bootstrap_servers)
                break
            except Exception:
                logger.exception("Kafka consumer start failed, retrying...")
                await asyncio.sleep(5)

        if not self._consumer:
            return

        try:
            async for message in self._consumer:
                try:
                    await self._handle_message(message.value)
                    await self._consumer.commit()
                except Exception:
                    logger.exception("Failed to process Kafka message: %s", message.value)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Kafka consumer failed")
        finally:
            await self.stop()

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
