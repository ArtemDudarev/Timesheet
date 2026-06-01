import asyncio
import json
import logging
import os
from typing import Any

from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)


class KafkaEventProducer:
    def __init__(self) -> None:
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        while True:
            try:
                self._producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                )
                await self._producer.start()
                logger.info("Kafka producer started: %s", self.bootstrap_servers)
                return
            except Exception:
                logger.exception("Kafka producer start failed, retrying...")
                await asyncio.sleep(5)

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        if not self._producer:
            raise RuntimeError("Kafka producer is not started")
        await self._producer.send_and_wait(topic, payload)
